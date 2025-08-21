"""
Sprint 108: Complete Multi-Channel System Integration Orchestrator

This module provides the comprehensive integration layer that connects all 
multi-channel architecture components from Sprints 103-107 into a cohesive 
system ready for production deployment.

Main responsibilities:
1. Initialize and coordinate all channel components with existing infrastructure
2. Provide unified entry points for all data sources (Tick, OHLCV, FMV)
3. Manage complete data flow from RealTimeAdapter through channels to WebSocket clients
4. Ensure performance targets and data integrity across the entire system
5. Provide monitoring and observability for the integrated system

Architecture:
- DataChannelRouter (Sprint 105): Intelligent routing of different data types
- Three Channel Types (Sprint 106): Tick, OHLCV, FMV processing channels
- EventProcessor Integration (Sprint 107): Multi-source event processing
- Existing Infrastructure: WebSocket publisher, priority manager, analytics
"""

import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from config.logging_config import get_domain_logger, LogDomain

# Core domain imports
from src.core.domain.market.tick import TickData
from src.shared.models.data_types import OHLCVData, FMVData, convert_to_typed_data

# Channel infrastructure (Sprint 105-106)
from src.processing.channels.channel_router import DataChannelRouter, RouterConfig, RoutingStrategy
from src.processing.channels.base_channel import ChannelStatus, ChannelType
from src.processing.channels.tick_channel import TickChannel, TickChannelConfig
from src.processing.channels.ohlcv_channel import OHLCVChannel, OHLCVChannelConfig
from src.processing.channels.fmv_channel import FMVChannel, FMVChannelConfig
from src.processing.channels.channel_metrics import ChannelMetrics

# Event processing (Sprint 107)
from src.processing.pipeline.event_processor import EventProcessingResult

logger = get_domain_logger(LogDomain.CORE, 'multi_channel_system')


class SystemIntegrationStatus(Enum):
    """Overall system integration status"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    DEGRADED = "degraded"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class IntegrationMetrics:
    """Comprehensive metrics for the integrated multi-channel system"""
    
    # Data flow metrics
    total_data_processed: int = 0
    tick_data_processed: int = 0
    ohlcv_data_processed: int = 0
    fmv_data_processed: int = 0
    
    # Performance metrics
    avg_end_to_end_latency_ms: float = 0.0
    peak_throughput_per_second: int = 0
    current_throughput_per_second: int = 0
    
    # Quality metrics
    successful_processings: int = 0
    failed_processings: int = 0
    data_integrity_violations: int = 0
    duplicate_events_detected: int = 0
    
    # System health metrics
    channels_healthy: int = 0
    channels_total: int = 0
    websocket_clients_connected: int = 0
    memory_usage_mb: float = 0.0
    
    # Timing tracking
    system_start_time: float = field(default_factory=time.time)
    last_activity_time: float = field(default_factory=time.time)
    
    def get_success_rate(self) -> float:
        """Calculate data processing success rate"""
        total = self.successful_processings + self.failed_processings
        return (self.successful_processings / total * 100.0) if total > 0 else 100.0
    
    def get_system_uptime_seconds(self) -> float:
        """Get system uptime in seconds"""
        return time.time() - self.system_start_time
    
    def get_channel_health_percentage(self) -> float:
        """Get percentage of healthy channels"""
        return (self.channels_healthy / self.channels_total * 100.0) if self.channels_total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for monitoring"""
        return {
            'data_flow': {
                'total_processed': self.total_data_processed,
                'tick_processed': self.tick_data_processed,
                'ohlcv_processed': self.ohlcv_data_processed,
                'fmv_processed': self.fmv_data_processed
            },
            'performance': {
                'avg_latency_ms': self.avg_end_to_end_latency_ms,
                'peak_throughput_per_sec': self.peak_throughput_per_second,
                'current_throughput_per_sec': self.current_throughput_per_second,
                'success_rate_percent': self.get_success_rate()
            },
            'quality': {
                'successful_processings': self.successful_processings,
                'failed_processings': self.failed_processings,
                'data_integrity_violations': self.data_integrity_violations,
                'duplicate_events_detected': self.duplicate_events_detected
            },
            'system_health': {
                'channels_healthy': self.channels_healthy,
                'channels_total': self.channels_total,
                'channel_health_percent': self.get_channel_health_percentage(),
                'websocket_clients': self.websocket_clients_connected,
                'memory_usage_mb': self.memory_usage_mb,
                'uptime_seconds': self.get_system_uptime_seconds()
            },
            'timestamps': {
                'system_start': self.system_start_time,
                'last_activity': self.last_activity_time
            }
        }


@dataclass
class MultiChannelSystemConfig:
    """Configuration for the complete multi-channel system"""
    
    # Channel configuration
    enable_tick_channel: bool = True
    enable_ohlcv_channel: bool = True
    enable_fmv_channel: bool = True
    
    # Routing configuration
    routing_strategy: RoutingStrategy = RoutingStrategy.HEALTH_BASED
    routing_timeout_ms: float = 50.0  # Sprint 108 requirement: <50ms
    
    # Performance targets (Sprint 108 requirements)
    target_ohlcv_symbols: int = 8000
    target_latency_p99_ms: float = 50.0
    target_memory_limit_gb: float = 2.0
    
    # Integration settings
    enable_websocket_integration: bool = True
    enable_priority_manager_integration: bool = True
    enable_analytics_integration: bool = True
    enable_monitoring: bool = True
    
    # Health and monitoring
    health_check_interval_seconds: float = 10.0
    metrics_collection_interval_seconds: float = 5.0
    performance_monitoring_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'channels': {
                'tick_enabled': self.enable_tick_channel,
                'ohlcv_enabled': self.enable_ohlcv_channel,
                'fmv_enabled': self.enable_fmv_channel
            },
            'routing': {
                'strategy': self.routing_strategy.value,
                'timeout_ms': self.routing_timeout_ms
            },
            'performance_targets': {
                'ohlcv_symbols': self.target_ohlcv_symbols,
                'latency_p99_ms': self.target_latency_p99_ms,
                'memory_limit_gb': self.target_memory_limit_gb
            },
            'integrations': {
                'websocket': self.enable_websocket_integration,
                'priority_manager': self.enable_priority_manager_integration,
                'analytics': self.enable_analytics_integration,
                'monitoring': self.enable_monitoring
            },
            'monitoring': {
                'health_check_interval': self.health_check_interval_seconds,
                'metrics_interval': self.metrics_collection_interval_seconds,
                'performance_monitoring': self.performance_monitoring_enabled
            }
        }


class MultiChannelSystem:
    """
    Complete multi-channel system integration orchestrator.
    
    Manages the coordination of all channel types with existing TickStock 
    infrastructure to provide a unified, high-performance data processing
    system ready for production deployment.
    """
    
    def __init__(self, config: MultiChannelSystemConfig, market_service=None):
        """
        Initialize the complete multi-channel system.
        
        Args:
            config: System configuration
            market_service: Reference to existing MarketDataService for integration
        """
        self.config = config
        self.market_service = market_service
        self.status = SystemIntegrationStatus.INITIALIZING
        self.metrics = IntegrationMetrics()
        
        # Core components
        self.channel_router: Optional[DataChannelRouter] = None
        self.tick_channel: Optional[TickChannel] = None
        self.ohlcv_channel: Optional[OHLCVChannel] = None
        self.fmv_channel: Optional[FMVChannel] = None
        
        # Integration references
        self.event_processor = None
        self.websocket_publisher = None
        self.priority_manager = None
        
        # Background tasks
        self._health_monitor_task = None
        self._metrics_collector_task = None
        self._running = False
        
        # Performance tracking
        self._latency_samples = []
        self._throughput_tracker = {'start_time': time.time(), 'count': 0}
        
        logger.info("MultiChannelSystem initialized with configuration")
        logger.info(f"Target performance: {config.target_ohlcv_symbols} OHLCV symbols, "
                   f"<{config.target_latency_p99_ms}ms latency, "
                   f"<{config.target_memory_limit_gb}GB memory")
    
    async def initialize_system(self) -> bool:
        """
        Initialize the complete multi-channel system with all integrations.
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("🚀 Initializing complete multi-channel system...")
            
            # Step 1: Extract integration references from market service
            if not self._extract_integration_references():
                logger.error("❌ Failed to extract integration references")
                return False
            
            # Step 2: Initialize channel router
            if not await self._initialize_channel_router():
                logger.error("❌ Failed to initialize channel router")
                return False
            
            # Step 3: Initialize individual channels
            if not await self._initialize_channels():
                logger.error("❌ Failed to initialize processing channels")
                return False
            
            # Step 4: Register channels with router
            if not self._register_channels_with_router():
                logger.error("❌ Failed to register channels with router")
                return False
            
            # Step 5: Integrate with existing event system
            if not self._integrate_with_event_system():
                logger.error("❌ Failed to integrate with event system")
                return False
            
            # Step 6: Integrate with WebSocket system
            if not self._integrate_with_websocket_system():
                logger.error("❌ Failed to integrate with WebSocket system")
                return False
            
            # Step 7: Start background monitoring
            if not await self._start_background_monitoring():
                logger.error("❌ Failed to start background monitoring")
                return False
            
            # Update system status
            self.status = SystemIntegrationStatus.READY
            self._running = True
            
            # Update metrics
            self._update_system_metrics()
            
            logger.info("✅ Multi-channel system initialization complete")
            logger.info(f"📊 System status: {self.status.value}")
            logger.info(f"📋 Channels initialized: {self._get_initialized_channel_summary()}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during system initialization: {e}", exc_info=True)
            self.status = SystemIntegrationStatus.ERROR
            return False
    
    def _extract_integration_references(self) -> bool:
        """Extract references to existing components for integration"""
        try:
            if not self.market_service:
                logger.error("No MarketDataService reference provided")
                return False
            
            # Extract event processor
            if hasattr(self.market_service, 'event_processor'):
                self.event_processor = self.market_service.event_processor
                logger.info("✅ EventProcessor reference extracted")
            else:
                logger.error("MarketDataService missing event_processor")
                return False
            
            # Extract WebSocket publisher
            if hasattr(self.market_service, 'websocket_publisher'):
                self.websocket_publisher = self.market_service.websocket_publisher
                logger.info("✅ WebSocketPublisher reference extracted")
            
            # Extract priority manager
            if hasattr(self.market_service, 'priority_manager'):
                self.priority_manager = self.market_service.priority_manager
                logger.info("✅ PriorityManager reference extracted")
            
            return True
            
        except Exception as e:
            logger.error(f"Error extracting integration references: {e}")
            return False
    
    async def _initialize_channel_router(self) -> bool:
        """Initialize the data channel router"""
        try:
            # Create router configuration
            router_config = RouterConfig(
                routing_strategy=self.config.routing_strategy,
                routing_timeout_ms=self.config.routing_timeout_ms,
                enable_load_balancing=True,
                enable_fallback_routing=True,
                health_check_interval=self.config.health_check_interval_seconds
            )
            
            # Initialize router
            self.channel_router = DataChannelRouter(router_config)
            
            # Set event processor reference for integration
            if self.event_processor:
                self.channel_router.set_event_processor(self.event_processor)
            
            # Start router
            await self.channel_router.start()
            
            logger.info("✅ DataChannelRouter initialized and started")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing channel router: {e}")
            return False
    
    async def _initialize_channels(self) -> bool:
        """Initialize all processing channels"""
        try:
            channels_initialized = 0
            
            # Initialize Tick Channel
            if self.config.enable_tick_channel:
                tick_config = TickChannelConfig(
                    max_queue_size=1000,
                    processing_timeout_ms=self.config.routing_timeout_ms,
                    enable_real_time_processing=True
                )
                self.tick_channel = TickChannel("primary_tick", tick_config)
                await self.tick_channel.start()
                channels_initialized += 1
                logger.info("✅ TickChannel initialized")
            
            # Initialize OHLCV Channel
            if self.config.enable_ohlcv_channel:
                ohlcv_config = OHLCVChannelConfig(
                    max_queue_size=self.config.target_ohlcv_symbols,
                    processing_timeout_ms=self.config.routing_timeout_ms * 2,  # OHLCV can be slower
                    batch_processing_enabled=True,
                    batch_size=100
                )
                self.ohlcv_channel = OHLCVChannel("primary_ohlcv", ohlcv_config)
                await self.ohlcv_channel.start()
                channels_initialized += 1
                logger.info("✅ OHLCVChannel initialized")
            
            # Initialize FMV Channel
            if self.config.enable_fmv_channel:
                fmv_config = FMVChannelConfig(
                    max_queue_size=500,
                    processing_timeout_ms=self.config.routing_timeout_ms,
                    confidence_threshold=0.8,
                    enable_validation=True
                )
                self.fmv_channel = FMVChannel("primary_fmv", fmv_config)
                await self.fmv_channel.start()
                channels_initialized += 1
                logger.info("✅ FMVChannel initialized")
            
            # Update metrics
            self.metrics.channels_total = channels_initialized
            self.metrics.channels_healthy = channels_initialized  # All start healthy
            
            logger.info(f"✅ Initialized {channels_initialized} processing channels")
            return channels_initialized > 0
            
        except Exception as e:
            logger.error(f"Error initializing channels: {e}")
            return False
    
    def _register_channels_with_router(self) -> bool:
        """Register all initialized channels with the router"""
        try:
            registered_channels = 0
            
            # Register Tick Channel
            if self.tick_channel:
                self.channel_router.register_channel(self.tick_channel)
                registered_channels += 1
                logger.debug("Tick channel registered with router")
            
            # Register OHLCV Channel
            if self.ohlcv_channel:
                self.channel_router.register_channel(self.ohlcv_channel)
                registered_channels += 1
                logger.debug("OHLCV channel registered with router")
            
            # Register FMV Channel
            if self.fmv_channel:
                self.channel_router.register_channel(self.fmv_channel)
                registered_channels += 1
                logger.debug("FMV channel registered with router")
            
            logger.info(f"✅ Registered {registered_channels} channels with router")
            return registered_channels > 0
            
        except Exception as e:
            logger.error(f"Error registering channels with router: {e}")
            return False
    
    def _integrate_with_event_system(self) -> bool:
        """Integrate the multi-channel system with existing event processing"""
        try:
            if not self.event_processor:
                logger.warning("No EventProcessor available for integration")
                return True  # Non-critical for basic functionality
            
            # Set channel router reference in event processor
            if hasattr(self.event_processor, 'set_channel_router'):
                self.event_processor.set_channel_router(self.channel_router)
                logger.info("✅ Channel router integrated with EventProcessor")
            
            # Verify multi-source data handling capability
            if hasattr(self.event_processor, 'handle_multi_source_data'):
                logger.info("✅ Multi-source data handling verified in EventProcessor")
            else:
                logger.warning("⚠️ EventProcessor missing handle_multi_source_data method")
            
            return True
            
        except Exception as e:
            logger.error(f"Error integrating with event system: {e}")
            return False
    
    def _integrate_with_websocket_system(self) -> bool:
        """Integrate with existing WebSocket publishing system"""
        try:
            if not self.config.enable_websocket_integration:
                logger.info("WebSocket integration disabled in configuration")
                return True
            
            if not self.websocket_publisher:
                logger.warning("No WebSocketPublisher available for integration")
                return True  # Non-critical
            
            # Verify WebSocket publisher has required capabilities
            if hasattr(self.websocket_publisher, 'market_service'):
                logger.info("✅ WebSocketPublisher integration verified")
                return True
            else:
                logger.warning("⚠️ WebSocketPublisher missing market_service reference")
                return True  # Still continue
            
        except Exception as e:
            logger.error(f"Error integrating with WebSocket system: {e}")
            return False
    
    async def _start_background_monitoring(self) -> bool:
        """Start background monitoring tasks"""
        try:
            # Start health monitoring
            if self.config.enable_monitoring:
                self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
                logger.info("✅ Health monitoring started")
            
            # Start metrics collection
            if self.config.performance_monitoring_enabled:
                self._metrics_collector_task = asyncio.create_task(self._metrics_collection_loop())
                logger.info("✅ Metrics collection started")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting background monitoring: {e}")
            return False
    
    async def process_tick_data(self, tick_data: TickData) -> Optional[EventProcessingResult]:
        """
        Process tick data through the multi-channel system.
        
        Args:
            tick_data: Incoming tick data
            
        Returns:
            EventProcessingResult: Processing result or None if failed
        """
        start_time = time.time()
        
        try:
            # Update metrics
            self.metrics.total_data_processed += 1
            self.metrics.tick_data_processed += 1
            self.metrics.last_activity_time = time.time()
            
            # Route through channel system
            result = await self.channel_router.route_data(tick_data)
            
            # Track performance
            latency_ms = (time.time() - start_time) * 1000
            self._track_latency(latency_ms)
            self._track_throughput()
            
            # Update success/failure metrics
            if result and result.success:
                self.metrics.successful_processings += 1
                logger.debug(f"✅ Tick data processed for {tick_data.ticker} in {latency_ms:.2f}ms")
            else:
                self.metrics.failed_processings += 1
                logger.warning(f"⚠️ Tick data processing failed for {tick_data.ticker}")
            
            return result
            
        except Exception as e:
            self.metrics.failed_processings += 1
            logger.error(f"❌ Error processing tick data: {e}", exc_info=True)
            return None
    
    async def process_ohlcv_data(self, ohlcv_data: Any) -> Optional[EventProcessingResult]:
        """
        Process OHLCV data through the multi-channel system.
        
        Args:
            ohlcv_data: OHLCV data (dict or typed object)
            
        Returns:
            EventProcessingResult: Processing result or None if failed
        """
        start_time = time.time()
        
        try:
            # Convert to typed data if needed
            if not isinstance(ohlcv_data, OHLCVData):
                if isinstance(ohlcv_data, dict):
                    ohlcv_data = convert_to_typed_data(ohlcv_data, 'ohlcv')
                else:
                    logger.error(f"Invalid OHLCV data type: {type(ohlcv_data)}")
                    return None
            
            # Update metrics
            self.metrics.total_data_processed += 1
            self.metrics.ohlcv_data_processed += 1
            self.metrics.last_activity_time = time.time()
            
            # Route through channel system
            result = await self.channel_router.route_data(ohlcv_data)
            
            # Track performance
            latency_ms = (time.time() - start_time) * 1000
            self._track_latency(latency_ms)
            self._track_throughput()
            
            # Update success/failure metrics
            if result and result.success:
                self.metrics.successful_processings += 1
                logger.debug(f"✅ OHLCV data processed for {ohlcv_data.ticker} in {latency_ms:.2f}ms")
            else:
                self.metrics.failed_processings += 1
                logger.warning(f"⚠️ OHLCV data processing failed for {ohlcv_data.ticker}")
            
            return result
            
        except Exception as e:
            self.metrics.failed_processings += 1
            logger.error(f"❌ Error processing OHLCV data: {e}", exc_info=True)
            return None
    
    async def process_fmv_data(self, fmv_data: Any) -> Optional[EventProcessingResult]:
        """
        Process FMV data through the multi-channel system.
        
        Args:
            fmv_data: FMV data (dict or typed object)
            
        Returns:
            EventProcessingResult: Processing result or None if failed
        """
        start_time = time.time()
        
        try:
            # Convert to typed data if needed
            if not isinstance(fmv_data, FMVData):
                if isinstance(fmv_data, dict):
                    fmv_data = convert_to_typed_data(fmv_data, 'fmv')
                else:
                    logger.error(f"Invalid FMV data type: {type(fmv_data)}")
                    return None
            
            # Update metrics
            self.metrics.total_data_processed += 1
            self.metrics.fmv_data_processed += 1
            self.metrics.last_activity_time = time.time()
            
            # Route through channel system
            result = await self.channel_router.route_data(fmv_data)
            
            # Track performance
            latency_ms = (time.time() - start_time) * 1000
            self._track_latency(latency_ms)
            self._track_throughput()
            
            # Update success/failure metrics
            if result and result.success:
                self.metrics.successful_processings += 1
                logger.debug(f"✅ FMV data processed for {fmv_data.ticker} in {latency_ms:.2f}ms")
            else:
                self.metrics.failed_processings += 1
                logger.warning(f"⚠️ FMV data processing failed for {fmv_data.ticker}")
            
            return result
            
        except Exception as e:
            self.metrics.failed_processings += 1
            logger.error(f"❌ Error processing FMV data: {e}", exc_info=True)
            return None
    
    def _track_latency(self, latency_ms: float):
        """Track end-to-end latency for performance monitoring"""
        self._latency_samples.append(latency_ms)
        
        # Keep only last 1000 samples for performance
        if len(self._latency_samples) > 1000:
            self._latency_samples = self._latency_samples[-1000:]
        
        # Update average latency
        self.metrics.avg_end_to_end_latency_ms = sum(self._latency_samples) / len(self._latency_samples)
    
    def _track_throughput(self):
        """Track throughput for performance monitoring"""
        current_time = time.time()
        self._throughput_tracker['count'] += 1
        
        # Calculate throughput every second
        time_elapsed = current_time - self._throughput_tracker['start_time']
        if time_elapsed >= 1.0:
            throughput = self._throughput_tracker['count'] / time_elapsed
            self.metrics.current_throughput_per_second = int(throughput)
            
            # Update peak throughput
            if throughput > self.metrics.peak_throughput_per_second:
                self.metrics.peak_throughput_per_second = int(throughput)
            
            # Reset tracker
            self._throughput_tracker = {'start_time': current_time, 'count': 0}
    
    def _update_system_metrics(self):
        """Update system-wide metrics"""
        try:
            # Update channel health counts
            healthy_channels = 0
            total_channels = 0
            
            for channel in [self.tick_channel, self.ohlcv_channel, self.fmv_channel]:
                if channel:
                    total_channels += 1
                    if channel.is_healthy():
                        healthy_channels += 1
            
            self.metrics.channels_healthy = healthy_channels
            self.metrics.channels_total = total_channels
            
            # Update WebSocket client count if available
            if (self.websocket_publisher and 
                hasattr(self.websocket_publisher, 'websocket_mgr') and 
                hasattr(self.websocket_publisher.websocket_mgr, 'get_active_connections')):
                self.metrics.websocket_clients_connected = len(
                    self.websocket_publisher.websocket_mgr.get_active_connections()
                )
            
        except Exception as e:
            logger.debug(f"Error updating system metrics: {e}")
    
    async def _health_monitor_loop(self):
        """Background health monitoring loop"""
        try:
            while self._running:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                
                if not self._running:
                    break
                
                # Update system metrics
                self._update_system_metrics()
                
                # Check system health
                health_issues = self._check_system_health()
                
                if health_issues:
                    logger.warning(f"System health issues detected: {health_issues}")
                    if len(health_issues) >= 3:  # Multiple critical issues
                        self.status = SystemIntegrationStatus.DEGRADED
                
                # Log periodic health status
                if self.metrics.total_data_processed > 0:
                    logger.info(f"🏥 System Health: {self.status.value} | "
                              f"Processed: {self.metrics.total_data_processed} | "
                              f"Success Rate: {self.metrics.get_success_rate():.1f}% | "
                              f"Avg Latency: {self.metrics.avg_end_to_end_latency_ms:.1f}ms | "
                              f"Channels: {self.metrics.channels_healthy}/{self.metrics.channels_total}")
                
        except asyncio.CancelledError:
            logger.info("Health monitor loop cancelled")
        except Exception as e:
            logger.error(f"Error in health monitor loop: {e}", exc_info=True)
    
    async def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        try:
            while self._running:
                await asyncio.sleep(self.config.metrics_collection_interval_seconds)
                
                if not self._running:
                    break
                
                # Collect router metrics
                if self.channel_router:
                    router_stats = self.channel_router.get_routing_statistics()
                    logger.debug(f"Router stats: {router_stats.get('total_routed', 0)} routed, "
                               f"{router_stats.get('routing_errors', 0)} errors")
                
                # Check performance targets
                self._check_performance_targets()
                
        except asyncio.CancelledError:
            logger.info("Metrics collection loop cancelled")
        except Exception as e:
            logger.error(f"Error in metrics collection loop: {e}", exc_info=True)
    
    def _check_system_health(self) -> List[str]:
        """Check system health and return list of issues"""
        issues = []
        
        # Check channel health
        if self.metrics.get_channel_health_percentage() < 100.0:
            issues.append(f"Unhealthy channels: {self.metrics.channels_total - self.metrics.channels_healthy}")
        
        # Check processing success rate
        if self.metrics.get_success_rate() < 95.0:
            issues.append(f"Low success rate: {self.metrics.get_success_rate():.1f}%")
        
        # Check latency
        if self.metrics.avg_end_to_end_latency_ms > self.config.target_latency_p99_ms:
            issues.append(f"High latency: {self.metrics.avg_end_to_end_latency_ms:.1f}ms")
        
        # Check for recent activity
        time_since_activity = time.time() - self.metrics.last_activity_time
        if time_since_activity > 300:  # 5 minutes
            issues.append(f"No recent activity: {time_since_activity:.0f}s")
        
        return issues
    
    def _check_performance_targets(self):
        """Check if system is meeting performance targets"""
        # Check latency target
        if (self.metrics.avg_end_to_end_latency_ms > self.config.target_latency_p99_ms and 
            len(self._latency_samples) > 100):
            logger.warning(f"⚠️ Latency target exceeded: "
                         f"{self.metrics.avg_end_to_end_latency_ms:.1f}ms > "
                         f"{self.config.target_latency_p99_ms}ms")
        
        # Check OHLCV processing capacity
        if self.metrics.ohlcv_data_processed > 0:
            # This is a simplified check - in practice, you'd need more sophisticated monitoring
            if self.metrics.current_throughput_per_second < (self.config.target_ohlcv_symbols / 60):
                logger.debug(f"OHLCV throughput: {self.metrics.current_throughput_per_second}/s")
    
    def _get_initialized_channel_summary(self) -> str:
        """Get summary of initialized channels"""
        channels = []
        if self.tick_channel:
            channels.append("Tick")
        if self.ohlcv_channel:
            channels.append("OHLCV")
        if self.fmv_channel:
            channels.append("FMV")
        return ", ".join(channels) if channels else "None"
    
    async def shutdown(self):
        """Gracefully shutdown the multi-channel system"""
        try:
            logger.info("🛑 Shutting down multi-channel system...")
            self.status = SystemIntegrationStatus.SHUTDOWN
            self._running = False
            
            # Cancel background tasks
            if self._health_monitor_task:
                self._health_monitor_task.cancel()
            if self._metrics_collector_task:
                self._metrics_collector_task.cancel()
            
            # Stop channels
            for channel in [self.tick_channel, self.ohlcv_channel, self.fmv_channel]:
                if channel:
                    await channel.stop()
            
            # Stop router
            if self.channel_router:
                await self.channel_router.stop()
            
            logger.info("✅ Multi-channel system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for monitoring"""
        return {
            'status': self.status.value,
            'config': self.config.to_dict(),
            'metrics': self.metrics.to_dict(),
            'channels': {
                'tick': {
                    'initialized': self.tick_channel is not None,
                    'healthy': self.tick_channel.is_healthy() if self.tick_channel else False,
                    'status': self.tick_channel.status.value if self.tick_channel else None
                },
                'ohlcv': {
                    'initialized': self.ohlcv_channel is not None,
                    'healthy': self.ohlcv_channel.is_healthy() if self.ohlcv_channel else False,
                    'status': self.ohlcv_channel.status.value if self.ohlcv_channel else None
                },
                'fmv': {
                    'initialized': self.fmv_channel is not None,
                    'healthy': self.fmv_channel.is_healthy() if self.fmv_channel else False,
                    'status': self.fmv_channel.status.value if self.fmv_channel else None
                }
            },
            'router': self.channel_router.get_routing_statistics() if self.channel_router else {},
            'integrations': {
                'event_processor': self.event_processor is not None,
                'websocket_publisher': self.websocket_publisher is not None,
                'priority_manager': self.priority_manager is not None
            },
            'performance_targets': {
                'latency_met': self.metrics.avg_end_to_end_latency_ms <= self.config.target_latency_p99_ms,
                'success_rate_met': self.metrics.get_success_rate() >= 95.0,
                'channels_healthy': self.metrics.get_channel_health_percentage() >= 100.0
            }
        }
    
    def is_system_ready(self) -> bool:
        """Check if system is ready for production use"""
        return (self.status in [SystemIntegrationStatus.READY, SystemIntegrationStatus.PROCESSING] and
                self.metrics.channels_healthy == self.metrics.channels_total and
                self.channel_router is not None)