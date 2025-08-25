"""
Core Market Data Service Orchestrator - Phase 5A
Main coordination class that manages all 6 refactored components.

PHASE 4: Updated for pure typed event processing - no dict compatibility.
This is the clean orchestration layer that replaces the monolithic market_data_service.py
"""

import logging
import time
import threading
import queue
import pytz
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from config.logging_config import get_domain_logger, LogDomain

from src.core.domain.market.tick import TickData
from src.presentation.converters.transport_models import StockData
from src.core.domain.events.surge import SurgeEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.highlow import HighLowEvent
# PHASE 4: Import BaseEvent for type checking
from src.core.domain.events.base import BaseEvent

# Import all 6 refactored components
from src.processing.pipeline.event_processor import EventProcessor, EventProcessingResult
from src.presentation.websocket.data_publisher import DataPublisher, PublishingResult
from src.core.services.universe_coordinator import UniverseCoordinator
from src.core.services.analytics_coordinator import AnalyticsCoordinator
from src.processing.workers.worker_pool import WorkerPoolManager
from src.monitoring.health_monitor import HealthMonitor
from src.processing.queues.priority_manager import PriorityManager

# Import supporting classes
from src.core.services.universe_service import TickStockUniverseManager
from src.core.services import AnalyticsManager
from src.presentation.websocket.publisher import WebSocketPublisher
# BuySellMarketTracker import removed - Phase 3 cleanup
from src.core.services import SessionAccumulationManager
from src.infrastructure.data_sources.adapters.realtime_adapter import SyntheticDataAdapter, RealTimeDataAdapter

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

logger = get_domain_logger(LogDomain.CORE, 'core_service')

# Data flow tracking
class CoreServiceStats:
    def __init__(self):
        self.startup_time = time.time()
        self.ticks_received = 0
        self.ticks_delegated = 0
        self.publish_attempts = 0
        self.publish_successes = 0
        self.status_updates = 0
        self.last_log_time = time.time()
        self.log_interval = 60  # seconds
        
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self, logger):
        uptime = time.time() - self.startup_time
        uptime_min = uptime / 60
        
        logger.info(f"📊CORE-SRVC: CORE SERVICE STATS (Uptime: {uptime_min:.1f}min): "
                   f"Ticks In:{self.ticks_received} → Delegated:{self.ticks_delegated} | "
                   f"Publish Attempts:{self.publish_attempts} → Success:{self.publish_successes} | "
                   f"Status Updates:{self.status_updates}")
        self.last_log_time = time.time()
    
    def check_health(self, logger):
        """Diagnose common failure modes"""
        if self.ticks_received == 0:
            logger.error("🚨CORE-SRVC:  NO TICKS RECEIVED - Check data source connection")
        elif self.ticks_delegated == 0:
            logger.error("🚨CORE-SRVC:  Ticks received but NOT DELEGATED - Check EventProcessor")
        elif self.publish_attempts == 0 and self.ticks_delegated > 0:
            logger.warning("⚠️CORE-SRVC:  Ticks processed but NO PUBLISH attempts - Check DataPublisher")
        elif self.publish_successes == 0 and self.publish_attempts > 0:
            logger.error("🚨CORE-SRVC:  Publish attempts but NO SUCCESSES - Check WebSocket connections")

@dataclass
class CoreServiceResult:
    """Result object for core service operations."""
    success: bool = True
    components_affected: int = 0
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    timestamp: float = None
    processing_time_ms: float = 0
    operation: str = "unknown"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

class MarketDataService:
    """
    Clean orchestration layer for market data processing.
    
    PHASE 4: All internal processing uses typed events exclusively.
    Dict conversion only happens at external boundaries (WebSocket emission).
    
    Coordinates 6 refactored components:
    1. EventProcessor - Tick processing & event detection
    2. DataPublisher - Per-user data routing & WebSocket emission  
    3. UniverseCoordinator - Universe management & user preferences
    4. AnalyticsCoordinator - Analytics & database synchronization
    5. WorkerPoolManager - Worker pool & event distribution
    6. HealthMonitor - System monitoring & performance tracking
    
    Responsibilities:
    - Initialize and coordinate all subsystems
    - Handle startup/shutdown sequences
    - Provide main API interface delegation
    - Manage high-level configuration and Flask integration
    """
    
    def __init__(self, config, data_provider, event_manager, websocket_mgr=None, cache_control=None):
        """
        Initialize core service and all 6 refactored components.
        
        Args:
            config: Application configuration
            data_provider: Data provider instance
            event_manager: Event detector instance
            websocket_mgr: Optional WebSocket manager for client communication
            cache_control: CacheControl instance for accessing cached data
        """
        start_time = time.time()
        
        # Store core dependencies
        self.config = config
        self.data_provider = data_provider
        self.event_manager = event_manager

        # Extract individual detectors for backward compatibility
        self.highlow_detector = event_manager.get_detector('highlow')
        self.trend_detector = event_manager.get_detector('trend')
        self.surge_detector = event_manager.get_detector('surge')


        self.websocket_mgr = websocket_mgr
        self.cache_control = cache_control
        
        # Initialize data flow tracking
        self.stats = CoreServiceStats()

        self._initialize_basic_properties()
        self._initialize_infrastructure()
        self._initialize_refactored_components()
        self._initialize_legacy_compatibility()
        self._initialize_real_time_adapter()
        self._validate_complete_architecture()
        self._establish_component_references()
        self._initialize_sprint_107_components()

        # Display queue for frontend events
        # Size: ~10KB per event * 10000 = ~100MB max memory
        self.display_queue = queue.Queue(maxsize=10000)
        
        # Display queue statistics
        self.display_queue_stats = {
            'events_queued': 0,
            'events_collected': 0,
            'queue_full_drops': 0,
            'max_depth_seen': 0
        }
        
        logger.info(f"📺 Display Queue initialized with max size: 10000")        
        
        initialization_time = (time.time() - start_time) * 1000
        logger.info(f"MarketDataService initialized in {initialization_time:.2f}ms")
        
    
    def _establish_component_references(self):
        """Establish bidirectional references between components after initialization."""
        try:
            # Set market_service reference on websocket components
            if self.websocket_mgr:
                self.websocket_mgr.market_service = self
            
            if self.websocket_publisher:
                self.websocket_publisher.market_service = self
            
            # Verify the references are working
            if hasattr(self.websocket_publisher, 'market_service'):
                has_priority_mgr = hasattr(self.websocket_publisher.market_service, 'priority_manager')
                
        except Exception as e:
            logger.error(f"❌ Error establishing component references: {e}")
    
    def _initialize_sprint_107_components(self):
        """SPRINT 107: Initialize multi-channel integration components"""
        try:
            # Initialize channel router from Sprint 105
            # Channel router removed - Phase 5 cleanup
            # from src.processing.channels.channel_router import DataChannelRouter, RouterConfig
            # self.channel_router = DataChannelRouter(router_config)
            
            # SPRINT 109 FIX: Register TickChannel for tick data processing
            from src.processing.channels.tick_channel import TickChannel
            from src.processing.channels.channel_config import TickChannelConfig
            tick_config = TickChannelConfig(name="primary_tick_config")
            tick_channel = TickChannel("primary_tick", tick_config)
            
            # SPRINT 109: Start channel immediately during registration (blocking)
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info(f"🔄 SPRINT 109: Starting TickChannel (ID: {id(tick_channel)}) during initialization...")
                start_result = loop.run_until_complete(tick_channel.start())
                logger.info(f"✅ SPRINT 109: TickChannel started successfully (ID: {id(tick_channel)}) - status={tick_channel.status.value}")
            except Exception as e:
                logger.error(f"❌ SPRINT 109: TickChannel startup failed during initialization: {e}", exc_info=True)
                raise
            
            self.tick_channel = tick_channel
            self.channel_router.register_channel(tick_channel)
            
            # SPRINT 109 DIAGNOSTIC: Verify registration worked
            from src.processing.channels.base_channel import ChannelType
            registered_channels = self.channel_router.channels.get(ChannelType.TICK, [])
            logger.info(f"✅ SPRINT 109: TickChannel registered with router (ID: {id(tick_channel)}) - Ready for routing")
            logger.info(f"🔍 SPRINT 109: Router has {len(registered_channels)} tick channels: {[ch.name for ch in registered_channels]}")
            if registered_channels:
                ch = registered_channels[0]
                logger.info(f"🔍 SPRINT 109: First channel status: {ch.name} status={ch.status.value} healthy={ch.is_healthy()}")
            
            # Connect channel router to event processor
            if hasattr(self, 'event_processor') and self.event_processor:
                self.event_processor.set_channel_router(self.channel_router)
            
            logger.info("✅ SPRINT 107: Multi-channel integration components initialized")
            
        except Exception as e:
            logger.error(f"❌ Error initializing Sprint 107 components: {e}", exc_info=True)
        
    def _initialize_basic_properties(self):
        """Initialize basic service properties."""
        # Data source configuration
        self.use_synthetic = self.config.get('USE_SYNTHETIC_DATA', False)
        self.use_polygon = self.config.get('USE_POLYGON_API', False)
        self.data_source = "Synthetic Data" if self.use_synthetic else (
            "Polygon.io API" if self.use_polygon else "Simulated Data")
        
        # Timezone setup
        self.eastern_tz = pytz.timezone(self.config.get('MARKET_TIMEZONE', 'US/Eastern'))
        
        # Processing state
        self.processing_active = False
        self.current_session = self._determine_session(datetime.now(self.eastern_tz))
        
        # Initialize PriorityManager (Sprint 6A component)
        self.priority_manager = PriorityManager(self.config)

        # Legacy compatibility properties (minimal set)
        self.stock_details: Dict[str, StockData] = {}
        self.changed_tickers = set()
        self.total_events_processed = 0
        self.sequence_counter = 0
        
        # API health tracking
        self.api_health = {
            "status": "healthy" if self.use_synthetic else "initializing",
            "last_success": time.time(),
            "failures": 0,
            "connected": True if self.use_synthetic else False,
            "rate_limit_remaining": 100,
            "response_times": []
        }
    
    def _initialize_stock_data(self, ticker: str) -> StockData:
        """Initialize StockData for a ticker - Sprint 21 addition"""
        if ticker not in self.stock_details:
            self.stock_details[ticker] = StockData(ticker=ticker)
        return self.stock_details[ticker]

        
    def _initialize_infrastructure(self):
        """Initialize supporting infrastructure components."""
        try:
            # Initialize TickStock Core Universe Manager
            self.tickstock_universe_manager = TickStockUniverseManager(self.cache_control)
            
            if not self.tickstock_universe_manager.build_core_universe():
                logger.error("❌CORE-SRVC:  Failed to build TickStock Core Universe during initialization")
                raise RuntimeError("CORE-SRVC: Core universe initialization failed")
            
            core_universe_size = self.tickstock_universe_manager.get_universe_size()
            core_universe_tickers = self.tickstock_universe_manager.get_core_universe()
            
            # Initialize centralized market metrics (NEW)
            from src.core.services.market_metrics import MarketMetrics
            self.market_metrics = MarketMetrics(self.config)

            self.websocket_publisher = WebSocketPublisher(self.websocket_mgr, self.config, self.cache_control)

            # Initialize UserSettingsService (ADD THIS)
            from src.core.services.user_settings_service import UserSettingsService
            self.user_settings_service = UserSettingsService()        

                
            # Initialize session accumulation manager
            self.session_accumulation_manager = SessionAccumulationManager()
            current_session_date = datetime.now(self.eastern_tz).date()
            self.session_accumulation_manager.initialize_session(current_session_date)
            
            # Initialize market analytics manager
            self.market_analytics_manager = AnalyticsManager()
            if hasattr(self.market_analytics_manager.memory_analytics, 'config'):
                self.market_analytics_manager.memory_analytics.config.update(self.config)
            self.market_analytics_manager.initialize_session(current_session_date)
            
            # Tracker components removed - Phase 3 cleanup
            # self.buysell_market_tracker = BuySellMarketTracker(self.config, self.cache_control)
            # self.trend_detector = TrendDetector(self.config, self.cache_control)
            # self.surge_detector = SurgeDetector(self.config, self.cache_control)
            
            logger.info("✅ Detector components disabled (Phase 3 cleanup)")
            
        except Exception as e:
            logger.error(f"❌ Error initializing infrastructure: {e}", exc_info=True)
            raise
    
    def _initialize_refactored_components(self):
        """Initialize all 6 refactored components in dependency order."""
        try:
            
            # Component 1: EventProcessor (depends on infrastructure)
            self.event_processor = EventProcessor(
                config=self.config,
                market_service=self,
                event_manager=self.event_manager,  
                buysell_market_tracker=self.buysell_market_tracker,
                session_accumulation_manager=self.session_accumulation_manager,
                market_analytics_manager=self.market_analytics_manager,
                cache_control=self.cache_control,
                market_metrics=self.market_metrics
            )
            
            # Component 2: DataPublisher (depends on infrastructure and WebSocket)
            self.data_publisher = DataPublisher(
                config=self.config,
                market_service=self,
                websocket_publisher=self.websocket_publisher,
                market_metrics=self.market_metrics
            )
            
            # SPRINT 29: NEW - Connect publishers for pull model
            if self.websocket_publisher and self.data_publisher:
                self.websocket_publisher.set_data_publisher(self.data_publisher)
                logger.info("✅ SPRINT 29: Connected DataPublisher → WebSocketPublisher (pull model enabled)"
                        f"📊 Collection interval: {self.config.get('COLLECTION_INTERVAL', 0.5)}s"
                        f"📤 Emission interval: {self.config.get('EMISSION_INTERVAL', 1.0)}s")
            else:
                logger.error("❌ SPRINT 29: Failed to connect publishers!")
                raise RuntimeError("Cannot establish pull model - missing publisher components")
            
            # Component 3: UniverseCoordinator (depends on infrastructure)
            self.universe_coordinator = UniverseCoordinator(
                config=self.config,
                market_service=self,
                cache_control=self.cache_control,
                tickstock_universe_manager=self.tickstock_universe_manager,
                websocket_publisher=self.websocket_publisher,
                buysell_market_tracker=self.buysell_market_tracker,
                user_settings_service=self.user_settings_service  
            )
            
            # Component 4: AnalyticsCoordinator (depends on analytics infrastructure)
            self.analytics_coordinator = AnalyticsCoordinator(
                config=self.config,
                market_service=self,
                session_accumulation_manager=self.session_accumulation_manager,
                market_analytics_manager=self.market_analytics_manager
            )
            
            # Component 5: WorkerPoolManager (depends on EventProcessor)
            self.worker_pool_manager = WorkerPoolManager(
                config=self.config,
                market_service=self,
                event_processor=self.event_processor
            )
            
            # Component 6: HealthMonitor (depends on WorkerPoolManager)
            self.health_monitor = HealthMonitor(
                config=self.config,
                market_service=self,
                websocket_mgr=self.websocket_mgr,
                worker_pool_manager=self.worker_pool_manager
            )
            
        except Exception as e:
            logger.error(f"❌ Error initializing refactored components: {e}", exc_info=True)
            raise
    
    def _initialize_legacy_compatibility(self):
        """Initialize legacy compatibility features."""
        try:
            # Universe tracking (for compatibility)
            from config.logging_config import get_domain_logger, LogDomain
            self.universe_logger = get_domain_logger(LogDomain.UNIVERSE_TRACKING, 'core_service')
            
            # Current user universe selections (will be updated via API calls)
            self.current_user_universes = {
                'market': ['DEFAULT_UNIVERSE'],
                'highlow': ['DEFAULT_UNIVERSE']
            }
            
            # Universe statistics tracking
            self.universe_stats = {
                'last_subscription_count': 0,
                'last_universe_count': 0,
                'last_overlap_count': 0,
                'last_coverage_percentage': 0,
                'last_stats_time': 0,
                'processing_stats': {
                    'total_ticks_received': 0,
                    'ticks_in_universe': 0,
                    'ticks_filtered_out': 0,
                    'filter_rate_percentage': 0
                }
            }
            
            # Event tracking for compatibility
            self.sent_high_events = set()
            self.sent_low_events = set()
            self.sent_surge_events = set()
            self.last_session = None
            
        except Exception as e:
            logger.error(f"❌ Error initializing legacy compatibility: {e}", exc_info=True)
            raise
    
    def _initialize_real_time_adapter(self):
        """Initialize real-time data adapter."""
        try:
            if self.use_synthetic:
                logger.info("🔌CORE-SRVC:  Using synthetic data adapter")
                self.real_time_adapter = SyntheticDataAdapter(
                    self.config, 
                    self.handle_websocket_tick, 
                    self.handle_websocket_status
                )
            elif self.use_polygon:
                logger.info("🔌 CORE-SRVC: Using Polygon.io real-time data adapter")
                self.real_time_adapter = RealTimeDataAdapter(
                    self.config, 
                    self.handle_websocket_tick, 
                    self.handle_websocket_status
                )
            else:
                logger.info("🔌 CORE-SRVC: No real-time adapter configured")
                self.real_time_adapter = None
            
        except Exception as e:
            logger.error(f"❌ Error initializing real-time adapter: {e}", exc_info=True)
            raise
    
    def register_with_app(self, app) -> CoreServiceResult:
        """
        Register market service with Flask application.
        
        Args:
            app: Flask application instance
            
        Returns:
            CoreServiceResult: Registration operation result
        """
        start_time = time.time()
        result = CoreServiceResult(operation="app_registration")
        
        try:
            # Register core service with app
            app.market_service = self
            app.websocket_publisher = self.websocket_publisher
            
            # Initialize filter cache if available
            if hasattr(self.websocket_publisher, 'initialize_filter_cache_safely'):
                with app.app_context():
                    cache_success = self.websocket_publisher.initialize_filter_cache_safely()
                    if cache_success:
                        result.components_affected += 1
                    else:
                        result.warnings.append("CORE-SRVC: Filter cache initialization skipped")
            
            result.components_affected += 1  # Core service registration
            
        except Exception as e:
            error_msg = f"Error registering market service with app: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    def _validate_complete_architecture(self):
        """Validate that all 6 components are properly initialized."""
        try:
            components = {
                'event_processor': self.event_processor,
                'data_publisher': self.data_publisher,
                'universe_coordinator': self.universe_coordinator,
                'analytics_coordinator': self.analytics_coordinator,
                'worker_pool_manager': self.worker_pool_manager,
                'health_monitor': self.health_monitor
            }
            
            missing_components = [name for name, component in components.items() if component is None]
            
            if missing_components:
                raise RuntimeError(f"Missing components: {missing_components}")
            
        except Exception as e:
            logger.error(f"❌ Architecture validation failed: {e}", exc_info=True)
            raise
    

    
    def start_processing(self) -> CoreServiceResult:
        """
        Start market data processing with all 6 components.
        Components are started in dependency order for reliable initialization.
        
        Returns:
            CoreServiceResult: Startup operation result
        """
        start_time = time.time()
        result = CoreServiceResult(operation="start_processing")
        
        if self.processing_active:
            result.warnings.append("Processing already active")
            return result
        
        try:
            self.processing_active = True
            
            # Step 1: Start real-time adapter connection
            if self.real_time_adapter:
                self._start_real_time_adapter()
                result.components_affected += 1
            
            # Step 2: Start WorkerPoolManager (manages event processing)
            worker_result = self.worker_pool_manager.start_workers(
                self.config.get('WORKER_POOL_SIZE', 4)
            )
            if worker_result.success:
                logger.info(f"✅CORE-SRVC:  WorkerPoolManager started: {worker_result.workers_affected} workers + dispatcher")
                result.components_affected += 1
            else:
                result.errors.extend(worker_result.errors)
                result.warnings.append("WorkerPoolManager startup issues")
            
            # Step 3: Start HealthMonitor (system monitoring)
            health_result = self.health_monitor.start()
            if health_result.success:
                logger.info(f"✅CORE-SRVC:  HealthMonitor started: {health_result.metrics_collected} monitoring threads")
                result.components_affected += 1
            else:
                result.errors.extend(health_result.errors)
                result.warnings.append("HealthMonitor startup issues")
            
            # Step 4: Start DataPublisher (publishing thread)
            if self.data_publisher.start_publishing_loop():
                logger.info("✅CORE-SRVC:  DataPublisher started successfully")
                result.components_affected += 1
            else:
                result.warnings.append("DataPublisher startup issues")
            
            # Step 4.5: SPRINT 109: TickChannel already started during initialization - skip duplicate startup
            if hasattr(self, 'tick_channel') and self.tick_channel:
                logger.info(f"✅CORE-SRVC: TickChannel already started during initialization (ID: {id(self.tick_channel)}) - status={self.tick_channel.status.value}")
                result.components_affected += 1
            
            # Step 5: Start WebSocket heartbeat
            self.websocket_publisher.start_heartbeat_loop(self.api_health, self.current_session)
            result.components_affected += 1
            
            logger.info(f"✅CORE-SRVC:  All processing threads started ({result.components_affected} components)")
            
        except Exception as e:
            error_msg = f"Error starting processing: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
            self.processing_active = False
        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    '''
    def stop_processing(self) -> CoreServiceResult:
        """
        Stop market data processing gracefully.
        Components are stopped in reverse dependency order.
        
        Returns:
            CoreServiceResult: Shutdown operation result
        """
        start_time = time.time()
        result = CoreServiceResult(operation="stop_processing")
        
        try:
            logger.info("🛑 Stopping market data processing")
            self.processing_active = False
            
            # Stop in reverse order
            # Step 1: Stop WebSocket heartbeat
            self.websocket_publisher.stop_heartbeat_loop()
            result.components_affected += 1
            
            # Step 2: Stop DataPublisher
            self.data_publisher.stop_publishing_loop()
            result.components_affected += 1
            
            # Step 3: Stop HealthMonitor
            health_result = self.health_monitor.stop()
            if health_result.success:
                result.components_affected += 1
            else:
                result.warnings.extend(health_result.warnings)
            
            # Step 4: Stop WorkerPoolManager
            worker_result = self.worker_pool_manager.stop_workers()
            if worker_result.success:
                result.components_affected += 1
            else:
                result.warnings.extend(worker_result.warnings)
            
            # Step 5: Stop real-time adapter
            if self.real_time_adapter:
                result.components_affected += 1
            
            logger.info(f"✅CORE-SRVC:  Market data processing stopped ({result.components_affected} components)")
            
        except Exception as e:
            error_msg = f"Error stopping processing: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
        
        return result
    '''
    # ===============================================================================
    # MAIN DATA PROCESSING METHODS - DELEGATE TO COMPONENTS
    # ===============================================================================
    def handle_websocket_tick(self, tick_data: TickData, ticker=None, timestamp=None) -> EventProcessingResult:
        """
        Main entry point for tick data - delegate to EventProcessor.
        PHASE 4: Processes typed TickData throughout the pipeline.
        
        Args:
            tick_data: Incoming WebSocket tick data (always typed)
            ticker: Optional ticker override
            timestamp: Optional timestamp override
            
        Returns:
            EventProcessingResult: Processing result from EventProcessor
        """
        
        try:
            # Check for market session change
            current_time = datetime.now(self.eastern_tz)
            current_session = self._determine_session(current_time)
            
            # Handle session change if needed
            self.handle_market_session_change(current_session, current_time)
            
            # Update current session
            self.current_session = current_session

            event_start_time = time.time()
            # TRACE
            if tick_data and tracer.should_trace(tick_data.ticker):
                tracer.trace(
                    ticker=tick_data.ticker,
                    component='CoreService',
                    action='tick_received',
                    data={
                        'input_count': ensure_int(1),  
                        'output_count': ensure_int(0),  # Not yet known
                        'duration_ms': ensure_int(0),   # Will calculate at end
                        'details': {
                            'price': tick_data.price,
                            'volume': tick_data.volume,
                            'timestamp': tick_data.timestamp,
                            'source': 'websocket'
                        }
                    }
                )


            start_time = time.time()
            
            # Track received tick
            self.stats.ticks_received += 1
            
            # Extract ticker for checkpoints
            tick_ticker = tick_data.ticker if tick_data else (ticker or 'unknown')
            
            # Log first few ticks
            if self.stats.ticks_received <= 25:
                logger.info(f"📥CORE-SRVC:  Confirmation CoreService received tick #{self.stats.ticks_received}: {tick_data.ticker} @ ${tick_data.price}")
            
            # Validate basic tick data
            if not tick_data or not tick_data.ticker or tick_data.price is None:
                logger.warning("⚠️CORE-SRVC:  Invalid tick data: missing ticker or price")
                
                return EventProcessingResult(
                    success=False,
                    errors=["Invalid tick data: missing ticker or price"],
                    ticker=tick_ticker
                )
            
            # SPRINT 107: Updated to route through channel system while maintaining compatibility
            # Check if multi-source integration is available
            if hasattr(self.event_processor, 'handle_multi_source_data'):
                # Use new multi-source pathway
                import asyncio
                if asyncio.iscoroutinefunction(self.event_processor.handle_multi_source_data):
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        # No event loop in thread - create new one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    processing_result = loop.run_until_complete(
                        self.event_processor.handle_multi_source_data(tick_data, "websocket_tick")
                    )
                else:
                    processing_result = self.event_processor.handle_multi_source_data(tick_data, "websocket_tick")
            else:
                # Fallback to original method for backward compatibility
                processing_result = self.event_processor.handle_tick(tick_data)
            
            # TRACE
            if tracer.should_trace(tick_ticker):
                tracer.trace(
                    ticker=tick_ticker,
                    component='CoreService',
                    action='tick_delegated',
                    data={
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(1 if processing_result.success else 0),
                        'duration_ms': (time.time() - event_start_time) * 1000,
                        'details': {
                            'success': processing_result.success,
                            'events_processed': processing_result.events_processed,
                            'errors': len(processing_result.errors)
                        }
                    }
                )


            if processing_result.success:
                self.stats.ticks_delegated += 1
            else:
                # SPRINT 109 DIAGNOSTIC: Log delegation failures
                logger.warning(f"🔍 DELEGATION FAILED for {tick_ticker}: {processing_result.errors if hasattr(processing_result, 'errors') else 'No error details'}")
            
            # Update API health based on processing result
            if processing_result.success:
                self.api_health["last_success"] = time.time()
                self.api_health["failures"] = max(0, self.api_health["failures"] - 1)
                if self.api_health["failures"] == 0:
                    self.api_health["status"] = "healthy"
            else:
                self.api_health["failures"] += 1
                if self.api_health["failures"] > 5:
                    self.api_health["status"] = "warning"
            
            # Track API performance
            elapsed_ms = (time.time() - start_time) * 1000
            self.api_health["response_times"].append(elapsed_ms)
            if len(self.api_health["response_times"]) > 10:
                self.api_health["response_times"].pop(0)
            
            # Periodic stats logging
            if self.stats.should_log():
                self.stats.log_stats(logger)
                self.stats.check_health(logger)

                # TRACE
                if self.stats.should_log():
                    if tracer.should_trace('SYSTEM'):
                        tracer.trace(
                            ticker='SYSTEM',
                            component='CoreService',
                            action='stats_update',
                            data={
                                'input_count': ensure_int(self.stats.ticks_received),
                                'output_count': ensure_int(self.stats.ticks_delegated),
                                'duration_ms': 0,
                                'details': {
                                    'publish_attempts': self.stats.publish_attempts,
                                    'publish_successes': self.stats.publish_successes,
                                    'uptime_minutes': (time.time() - self.stats.startup_time) / 60
                                }
                            }
                        )

            
            return processing_result
            
        except Exception as e:
            error_msg = f"Error in CoreService WebSocket tick handler: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            
            return EventProcessingResult(
                success=False,
                errors=[error_msg],
                ticker=tick_ticker
            )
    
    async def handle_ohlcv_data(self, ohlcv_data) -> EventProcessingResult:
        """
        SPRINT 107: New entry point for OHLCV channel integration.
        Processes OHLCV aggregate data with source-specific rules.
        
        Args:
            ohlcv_data: OHLCV data object or dictionary
            
        Returns:
            EventProcessingResult: Processing result from multi-source coordinator
        """
        try:
            self.stats.ticks_received += 1
            
            # Convert to typed data if needed
            from src.shared.models.data_types import OHLCVData, convert_to_typed_data
            
            if not isinstance(ohlcv_data, OHLCVData):
                if isinstance(ohlcv_data, dict):
                    ohlcv_data = convert_to_typed_data(ohlcv_data, 'ohlcv')
                else:
                    logger.error(f"❌ Invalid OHLCV data type: {type(ohlcv_data)}")
                    return EventProcessingResult(
                        success=False,
                        errors=["Invalid OHLCV data format"],
                        ticker=getattr(ohlcv_data, 'ticker', 'unknown')
                    )
            
            # Log first few OHLCV entries
            if self.stats.ticks_received <= 10:
                logger.info(f"📊 SPRINT 107: OHLCV data #{self.stats.ticks_received}: {ohlcv_data}")
            
            # Process through multi-source system
            result = await self.event_processor.handle_multi_source_data(ohlcv_data, "ohlcv_channel")
            
            if result.success:
                self.stats.ticks_delegated += 1
                logger.debug(f"✅ OHLCV data processed for {ohlcv_data.ticker}: {result.events_processed} events")
            else:
                logger.warning(f"⚠️ OHLCV processing failed for {ohlcv_data.ticker}: {result.errors}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error in OHLCV data handler: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            
            return EventProcessingResult(
                success=False,
                errors=[error_msg],
                ticker=getattr(ohlcv_data, 'ticker', 'unknown')
            )
    
    async def handle_fmv_data(self, fmv_data) -> EventProcessingResult:
        """
        SPRINT 107: New entry point for FMV channel integration.
        Processes Fair Market Value data with confidence filtering.
        
        Args:
            fmv_data: FMV data object or dictionary
            
        Returns:
            EventProcessingResult: Processing result from multi-source coordinator
        """
        try:
            self.stats.ticks_received += 1
            
            # Convert to typed data if needed
            from src.shared.models.data_types import FMVData, convert_to_typed_data
            
            if not isinstance(fmv_data, FMVData):
                if isinstance(fmv_data, dict):
                    fmv_data = convert_to_typed_data(fmv_data, 'fmv')
                else:
                    logger.error(f"❌ Invalid FMV data type: {type(fmv_data)}")
                    return EventProcessingResult(
                        success=False,
                        errors=["Invalid FMV data format"],
                        ticker=getattr(fmv_data, 'ticker', 'unknown')
                    )
            
            # Log first few FMV entries
            if self.stats.ticks_received <= 10:
                logger.info(f"💰 SPRINT 107: FMV data #{self.stats.ticks_received}: {fmv_data}")
            
            # Process through multi-source system
            result = await self.event_processor.handle_multi_source_data(fmv_data, "fmv_channel")
            
            if result.success:
                self.stats.ticks_delegated += 1
                logger.debug(f"✅ FMV data processed for {fmv_data.ticker}: {result.events_processed} events")
            else:
                logger.warning(f"⚠️ FMV processing failed for {fmv_data.ticker}: {result.errors}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error in FMV data handler: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            
            return EventProcessingResult(
                success=False,
                errors=[error_msg],
                ticker=getattr(fmv_data, 'ticker', 'unknown')
            )
    
    def handle_websocket_status(self, status, extra_info=None) -> CoreServiceResult:
        """
        Handle WebSocket status updates with component coordination.
        
        Args:
            status: Status string
            extra_info: Optional additional information
            
        Returns:
            CoreServiceResult: Status handling result
        """
        start_time = time.time()
        result = CoreServiceResult(operation="status_update")
        
        try:
            self.stats.status_updates += 1
            
            # Update API health based on status
            if status == 'connected':
                self.api_health["status"] = "healthy"
                self.api_health["connected"] = True
                self.api_health["last_success"] = time.time()
                self.api_health["failures"] = 0
                logger.info("✅CORE-SRVC:  WebSocket connected")
            elif status == 'disconnected':
                self.api_health["connected"] = False
                self.api_health["status"] = "warning" if self.api_health["failures"] < 3 else "error"
                logger.warning("⚠️CORE-SRVC:  WebSocket disconnected")
            elif status == 'error':
                self.api_health["failures"] += 1
                self.api_health["status"] = "warning" if self.api_health["failures"] <= 3 else "error"
                logger.error("❌CORE-SRVC:  WebSocket error")
            
            # Send status update via WebSocket publisher
            if self.websocket_mgr:
                if extra_info is None:
                    extra_info = {}
                
                # Add data source information
                if 'provider' not in extra_info:
                    extra_info['provider'] = self.data_source
                
                self.websocket_publisher.send_status_update(status, extra_info)
                result.components_affected += 1
            
        except Exception as e:
            error_msg = f"Error handling WebSocket status: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
        
        return result
    
    '''
    def publish_stock_data(self) -> PublishingResult:
        """
        Publish data to authenticated users - delegate to DataPublisher.
        
        Returns:
            PublishingResult: Publishing operation result
        """
        try:
            self.stats.publish_attempts += 1
            
            # Delegate to DataPublisher
            publishing_result = self.data_publisher.publish_to_users()
            
            if publishing_result.success:
                self.stats.publish_successes += 1
                # MODIFIED: Don't log every success in pull model, just track stats
                if self.stats.publish_successes <= 3 or self.stats.publish_successes % 100 == 0:
                    logger.info(f"📤CORE-SRVC: Buffer collection #{self.stats.publish_successes} "
                            f"({publishing_result.events_published} events buffered)")            
                    
            return publishing_result
            
        except Exception as e:
            error_msg = f"Error in CoreService stock data publication: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            return PublishingResult(
                success=False,
                errors=[error_msg],
                publishing_method="core_service_delegation"
            )
    '''
    def update_user_universe_selections(self, user_id: int, tracker_type: str, universes: List[str]) -> bool:
        """
        Update universe selections - delegate to UniverseCoordinator.
        
        Args:
            user_id: User identifier
            tracker_type: Type of tracker ('market' or 'highlow')
            universes: List of universe names
            
        Returns:
            bool: Success status
        """
        try:
            # Delegate to UniverseCoordinator
            result = self.universe_coordinator.update_user_universe_selections(user_id, tracker_type, universes)
            
            if result.success:
                logger.info(f"✅CORE-SRVC:  Updated universe for user {user_id}: {tracker_type} → {universes}")
            
            return result.success
            
        except Exception as e:
            logger.error(f"❌ Error in CoreService universe update delegation: {e}", exc_info=True)
            return False
    
    def get_market_status(self) -> str:
        """
        Get current market status.
        
        Returns:
            str: Current market status
        """
        return self.current_session or "REGULAR"
    
    def _start_real_time_adapter(self):
        """Start real-time adapter connection in background thread."""
        if not self.real_time_adapter:
            return
        
        try:
            # Get default universe for connection
            tickers = self.cache_control.get_default_universe()
            
            # Log subscription analysis via UniverseCoordinator
            self.universe_coordinator.log_subscription_universe_analysis(tickers)
            
            logger.info(f"🔌 CORE-SRVC: Connecting real-time adapter to {len(tickers)} tickers")
            
            # Handle connection with or without startup delay
            if not self.use_synthetic and self.use_polygon:
                startup_delay = self.config.get('WEBSOCKET_STARTUP_DELAY', 30)
                if startup_delay > 0:
                    logger.info(f"⏱️CORE-SRVC:  Setting {startup_delay}s startup delay for WebSocket connection stabilization")
                    self.connection_ready = threading.Event()
                    connection_thread = threading.Thread(
                        target=self._connect_and_wait,
                        args=(startup_delay,),
                        daemon=True,
                        name="real-time-adapter-connection-with-delay"
                    )
                    connection_thread.start()
                    return
            
            # Standard connection
            connection_thread = threading.Thread(
                target=self._connect_real_time_adapter,
                daemon=True,
                name="real-time-adapter-connection"
            )
            connection_thread.start()
            
        except Exception as e:
            logger.error(f"❌ Error starting real-time adapter: {e}", exc_info=True)
    
    def _connect_real_time_adapter(self):
        """Handle real-time adapter connection."""
        try:
            tickers = self.cache_control.get_default_universe()
            
            if (self.real_time_adapter and 
                self.real_time_adapter.client and 
                self.real_time_adapter.client.connected):
                logger.info("✅CORE-SRVC:  WebSocket already connected, skipping reconnection attempt")
                self.handle_websocket_status('connected')
                self.real_time_adapter.client.check_subscriptions()
                return 
                        
             # Attempt connection with retries
            for attempt in range(3):
               if self.real_time_adapter.connect(tickers):
                   logger.info("✅CORE-SRVC:  WebSocket connection established successfully")
                   self.handle_websocket_status('connected')
                   return
               else:
                   logger.warning(f"⚠️CORE-SRVC:  WebSocket connection attempt {attempt+1}/3 failed, retrying")
                   time.sleep(5)
           
            logger.error("❌CORE-SRVC:  Failed to establish WebSocket connection after all attempts")
           
        except Exception as e:
           logger.error(f"❌ Error in real-time adapter connection: {e}", exc_info=True)

    def _connect_and_wait(self, delay_seconds: int):
        """Connect to real-time adapter and wait for stabilization."""
        try:
            # First establish the connection
            self._connect_real_time_adapter()
            
            # Wait for stabilization
            logger.info(f"⏱️CORE-SRVC:  WebSocket connection initiated, waiting {delay_seconds}s for stabilization")
            time.sleep(delay_seconds)
            logger.info("✅CORE-SRVC:  WebSocket stabilization period complete")
            
            # Signal completion
            if hasattr(self, 'connection_ready'):
                self.connection_ready.set()
                
        except Exception as e:
            logger.error(f"❌CORE-SRVC:  Error in connection with delay: {e}", exc_info=True)
            if hasattr(self, 'connection_ready'):
                self.connection_ready.set()
    
    def _determine_session(self, current_time) -> str:
        """
        Determine market session based on eastern time.
        
        Args:
            current_time: Current datetime in Eastern timezone
            
        Returns:
            str: Market status ("PRE", "REGULAR", "AFTER", or "CLOSED")
        """
        hour, minute = current_time.hour, current_time.minute
        if 4 <= hour < 9 or (hour == 9 and minute < 30):
            return "PRE"
        elif (hour == 9 and minute >= 30) or (10 <= hour < 16):
            return "REGULAR"
        elif 16 <= hour < 20:
            return "AFTER"
        return "CLOSED"
    

    def handle_market_session_change(self, new_session: str, current_time: datetime):
        """Handle market session transitions and reset counts when appropriate."""
        
        # Get previous session
        previous_session = getattr(self, 'last_market_session', None)
        
        if previous_session == new_session:
            return  # No change
        
        # Log session transition
        logger.info(f"📅 Market session change: {previous_session} → {new_session} at {current_time.strftime('%H:%M:%S ET')}")
        
        # Determine if we should reset counts
        should_reset = False
        reset_reason = ""
        
        # Reset scenarios:
        # 1. Overnight reset: CLOSED/AFTER → PRE (new trading day begins)
        if previous_session in ['CLOSED', 'AFTER'] and new_session == 'PRE':
            should_reset = True
            reset_reason = "Pre-market open - new trading day"
        
        # 2. Market open reset: PRE → REGULAR (opening bell)
        elif previous_session == 'PRE' and new_session == 'REGULAR':
            should_reset = True
            reset_reason = "Market open - opening bell"
        
        # No reset scenarios:
        # - REGULAR → AFTER (closing bell - counts continue)
        # - Any other transitions
        
        if should_reset:
            # Update market metrics session
            self.market_metrics.reset_session_counts(reset_reason)
            self.market_metrics.set_market_session(new_session, current_time)
            
            # Reset accumulation manager with current date
            current_date = current_time.date()
            self.session_accumulation_manager.initialize_session(current_date)
            
            # Clear event tracking sets
            if hasattr(self, 'sent_high_events'):
                self.sent_high_events.clear()
            if hasattr(self, 'sent_low_events'):
                self.sent_low_events.clear()
            
            # Reset stock details event counts
            for stock_data in self.stock_details.values():
                stock_data.event_counts.highs = 0
                stock_data.event_counts.lows = 0
                stock_data.highlow_bar.high_count = 0
                stock_data.highlow_bar.low_count = 0
            
            # Log reset completion
            logger.info(f"✅ Session counts reset completed for {new_session}")
            
            # Optionally emit a status update to notify frontend
            if self.websocket_publisher:
                self.websocket_publisher.send_status_update(
                    'session_reset',
                    {
                        'new_session': new_session,
                        'reset_time': current_time.isoformat(),
                        'reset_reason': reset_reason
                    }
                )
        
        # Update last session
        self.last_market_session = new_session



    # =========================================================================
    # Component Validation and Statistics Methods
    # =========================================================================
    '''
    def validate_complete_architecture_integration(self) -> Dict[str, Any]:
        """Validate complete Phase 5A architecture integration (all 6 components)."""
        try:
            validation_results = {
                'core_service_initialized': True,
                'component_validation': {},
                'overall_status': 'unknown',
                'validation_timestamp': time.time()
            }
            
            # Validate each component
            components = {
                'event_processor': self.event_processor,
                'data_publisher': self.data_publisher,
                'universe_coordinator': self.universe_coordinator,
                'analytics_coordinator': self.analytics_coordinator,
                'worker_pool_manager': self.worker_pool_manager,
                'health_monitor': self.health_monitor
            }
            
            ready_components = 0
            for name, component in components.items():
                try:
                    if hasattr(component, 'get_performance_report'):
                        component_report = component.get_performance_report()
                        validation_results['component_validation'][name] = {
                            'initialized': True,
                            'status': 'ready',
                            'performance': component_report
                        }
                        ready_components += 1
                    else:
                        validation_results['component_validation'][name] = {
                            'initialized': True,
                            'status': 'ready',
                            'note': 'No performance report available'
                        }
                        ready_components += 1
                except Exception as e:
                    validation_results['component_validation'][name] = {
                        'initialized': True,
                        'status': 'error',
                        'error': str(e)
                    }
            
            # Overall status determination
            if ready_components == 6:
                validation_results['overall_status'] = 'ready'
            elif ready_components >= 4:
                validation_results['overall_status'] = 'partial'
            else:
                validation_results['overall_status'] = 'not_ready'
            
            # Architecture summary
            validation_results['architecture_summary'] = {
                'components_ready': ready_components,
                'total_components': 6,
                'readiness_percentage': (ready_components / 6) * 100,
                'architecture_status': 'Phase 5A Complete' if ready_components == 6 else f'Phase 5A - {ready_components}/6 ready',
                'core_service_active': True
            }
            
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ Error validating Phase 5A architecture: {e}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'validation_timestamp': time.time()
            }
    '''
    def get_display_queue_status(self) -> Dict[str, Any]:
        """Get display queue statistics."""
        try:
            current_size = self.display_queue.qsize()
            
            return {
                'current_size': current_size,
                'max_size': self.display_queue.maxsize,
                'utilization_percent': round((current_size / self.display_queue.maxsize) * 100, 2),
                'events_queued': self.display_queue_stats['events_queued'],
                'events_collected': self.display_queue_stats['events_collected'],
                'queue_full_drops': self.display_queue_stats['queue_full_drops'],
                'max_depth_seen': self.display_queue_stats['max_depth_seen'],
                'collection_efficiency': round(
                    (self.display_queue_stats['events_collected'] / 
                    self.display_queue_stats['events_queued'] * 100)
                    if self.display_queue_stats['events_queued'] > 0 else 0, 2
                )
            }
        except Exception as e:
            logger.error(f"Error getting display queue status: {e}")
            return {'error': str(e)}

    '''
    def get_core_service_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report from CoreService."""
        try:
            # Check data flow health
            self.stats.check_health(logger)
            
            return {
                'core_service': {
                    'processing_active': self.processing_active,
                    'total_events_processed': self.total_events_processed,
                    'api_health': self.api_health.copy(),
                    'data_source': self.data_source,
                    'current_session': self.current_session
                },
                'data_flow_stats': {
                    'ticks_received': self.stats.ticks_received,
                    'ticks_delegated': self.stats.ticks_delegated,
                    'publish_attempts': self.stats.publish_attempts,
                    'publish_successes': self.stats.publish_successes,
                    'status_updates': self.stats.status_updates,
                    'uptime_seconds': time.time() - self.stats.startup_time
                },
                'component_reports': {
                    'event_processor': self.event_processor.get_performance_report() if hasattr(self.event_processor, 'get_performance_report') else {},
                    'data_publisher': self.data_publisher.get_performance_report() if hasattr(self.data_publisher, 'get_performance_report') else {},
                    'universe_coordinator': self.universe_coordinator.get_performance_report() if hasattr(self.universe_coordinator, 'get_performance_report') else {},
                    'analytics_coordinator': self.analytics_coordinator.get_performance_report() if hasattr(self.analytics_coordinator, 'get_performance_report') else {},
                    'worker_pool_manager': self.worker_pool_manager.get_performance_report() if hasattr(self.worker_pool_manager, 'get_performance_report') else {},
                    'health_monitor': self.health_monitor.get_performance_report() if hasattr(self.health_monitor, 'get_performance_report') else {}
                },
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"❌ Error generating CoreService performance report: {e}")
            return {'error': str(e)}
    '''
    # =========================================================================
    # Legacy Compatibility Methods (Minimal Set) Auto Generated Prior
    # PHASE 4: Updated to work with typed StockData and events
    # =========================================================================
    '''
    def get_trending_stocks(self, min_strength='weak', max_results=20):
        """
        Get trending stocks - Uses event-based system with StockData objects.
        PHASE 4: Now properly handles typed StockData exclusively.
        """
        try:
            current_time = time.time()
            strength_scores = {'weak': 1, 'moderate': 2, 'strong': 3}
            min_score = strength_scores.get(min_strength, 1)
            
            up_trending = []
            down_trending = []
            
            # Check stock_details for stocks with active trends
            for ticker, stock_data in self.stock_details.items():
                # PHASE 4: Direct typed access only
                trend_direction = stock_data.trend_direction
                trend_strength = stock_data.trend_strength
                trend_score = stock_data.trend_score
                last_trend_update = stock_data.last_update
                
                # Skip if no trend or below minimum strength
                if trend_direction == '→' or strength_scores.get(trend_strength, 0) < min_score:
                    continue
                    
                # Skip if trend is too old (5 minutes)
                if last_trend_update and current_time - last_trend_update > 300:
                    continue
                
                # Build trend data structure
                trend_data = {
                    'ticker': ticker,
                    'price': stock_data.last_price,
                    'trend_strength': trend_strength,
                    'trend_score': trend_score,
                    'vwap_position': stock_data.vwap_position,
                    'vwap_divergence': stock_data.vwap_divergence,
                    'last_trend_update': datetime.fromtimestamp(last_trend_update).isoformat() if last_trend_update else None,
                    # Sprint 17 fields
                    'reversal': None,
                    'count_up': 0,
                    'count_down': 0,
                    'count': 0,
                    'direction': 'up' if trend_direction == '↑' else 'down',
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'label': trend_strength,
                    'percent_change': stock_data.percent_change
                }
                
                # Get trend event counts from recent events
                recent_trend_events = [e for e in stock_data.events if isinstance(e, TrendEvent) and e.time > current_time - 300]
                if recent_trend_events:
                    latest_trend = recent_trend_events[-1]
                    trend_data['count_up'] = latest_trend.count_up
                    trend_data['count_down'] = latest_trend.count_down
                    trend_data['count'] = latest_trend.count
                    trend_data['reversal'] = latest_trend.reversal
                
                # Add to appropriate list
                if trend_direction == '↑':
                    up_trending.append(trend_data)
                elif trend_direction == '↓':
                    down_trending.append(trend_data)
            
            # Sort by trend score (absolute value) and limit
            up_trending.sort(key=lambda x: abs(x['trend_score']), reverse=True)
            down_trending.sort(key=lambda x: abs(x['trend_score']), reverse=True)
            
            up_trending = up_trending[:max_results]
            down_trending = down_trending[:max_results]
            
            # Clean up old trend tracking
            if not hasattr(self, 'last_trend_cleanup_time'):
                self.last_trend_cleanup_time = current_time
            
            if current_time - self.last_trend_cleanup_time > 300:
                if hasattr(self.trend_detector, 'cleanup_trend_tracking'):
                    self.trend_detector.cleanup_trend_tracking()
                self.last_trend_cleanup_time = current_time
            
            return {
                'up_trending': up_trending,
                'down_trending': down_trending
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting trending stocks: {e}", exc_info=True)
            return {'up_trending': [], 'down_trending': []}
    '''

    '''
    def get_surging_stocks(self, min_strength='weak', max_results=50, min_recency=30, only_new=True):
        """
        Get surging stocks - Extracts recent surge events from StockData objects.
        PHASE 4: Now properly handles typed events in StockData exclusively.
        """
        try:
            current_time = time.time()
            strength_scores = {'weak': 30, 'moderate': 60, 'strong': 80}
            min_score = strength_scores.get(min_strength, 30)
            
            surge_events = []
            
            # Check stock_details for stocks with surge events
            for ticker, stock_data in self.stock_details.items():
                # PHASE 4: Direct typed access only
                # Get recent surge events from StockData
                recent_surges = [e for e in stock_data.events if isinstance(e, SurgeEvent) and e.time > current_time - min_recency]
                
                for surge in recent_surges:
                    # Check score threshold
                    if surge.surge_score < min_score:
                        continue
                    
                    # Check if already sent (if only_new is True)
                    surge_id = f"{ticker}_{surge.direction}_{surge.time}"
                    if only_new and hasattr(self, 'sent_surge_events'):
                        if surge_id in self.sent_surge_events:
                            continue
                    
                    # Format the surge event
                    formatted_surge = {
                        'ticker': ticker,
                        'price': surge.price,
                        'direction': surge.direction,
                        'magnitude': surge.surge_magnitude,
                        'score': surge.surge_score,
                        'strength': surge.surge_strength,
                        'trigger_type': surge.surge_trigger_type,
                        'description': surge.surge_description,
                        'time': datetime.fromtimestamp(surge.time).strftime('%H:%M:%S'),
                        'volume_multiplier': surge.surge_volume_multiplier,
                        'event_key': surge_id,
                        'surge_age': current_time - surge.time,
                        'expiration': surge.surge_expiration,
                        'daily_surge_count': surge.surge_daily_count,
                        'last_surge_timestamp': surge.time,
                        # Sprint 17 fields
                        'reversal': surge.reversal,
                        'count_up': surge.count_up,
                        'count_down': surge.count_down,
                        'count': surge.count,
                        'percent_change': surge.surge_magnitude
                    }
                    
                    surge_events.append(formatted_surge)
                    
                    # Mark as sent if tracking
                    if only_new:
                        if not hasattr(self, 'sent_surge_events'):
                            self.sent_surge_events = set()
                        self.sent_surge_events.add(surge_id)
            
            # Remove duplicates by keeping highest score per ticker
            ticker_surges = {}
            for surge in surge_events:
                ticker = surge['ticker']
                if ticker not in ticker_surges or surge['score'] > ticker_surges[ticker]['score']:
                    ticker_surges[ticker] = surge
            
            # Convert back to list and sort
            formatted_surges = list(ticker_surges.values())
            formatted_surges.sort(key=lambda x: x['score'], reverse=True)
            formatted_surges = formatted_surges[:max_results]
            
            # Clean up old sent surge events periodically
            if hasattr(self, 'sent_surge_events') and len(self.sent_surge_events) > 1000:
                # Keep only recent surge IDs
                recent_surge_ids = set()
                for surge_id in self.sent_surge_events:
                    try:
                        # Extract timestamp from surge_id
                        parts = surge_id.rsplit('_', 1)
                        if len(parts) == 2 and parts[1].replace('.', '').isdigit():
                            surge_time = float(parts[1])
                            if current_time - surge_time < 3600:  # Keep last hour
                                recent_surge_ids.add(surge_id)
                    except:
                        pass
                self.sent_surge_events = recent_surge_ids
            
            return formatted_surges
            
        except Exception as e:
            logger.error(f"❌ Error getting surging stocks: {e}", exc_info=True)
            return []
    '''
    def get_analytics_for_websocket(self) -> Dict[str, Any]:
        """
        Get analytics data for WebSocket emission, including session totals.
        
        Returns:
            dict: Analytics data with session totals, market stats, etc.
        """
        try:
            analytics_data = {}
            
            # Get activity metrics from centralized location (NEW)
            if hasattr(self, 'market_metrics'):
                analytics_data['activity_metrics'] = self.market_metrics.get_activity_metrics()
                
            # Get session totals from accumulation manager
            if hasattr(self, 'session_accumulation_manager'):
                session_totals = self.session_accumulation_manager.get_session_totals()
                analytics_data['session_totals'] = session_totals
                logger.debug(f"📊 Retrieved session totals: {session_totals}")
            else:
                logger.warning("⚠️ No session_accumulation_manager available")
                analytics_data['session_totals'] = {
                    'total_highs': 0,
                    'total_lows': 0,
                    'total_events': 0
                }
            
            # Get analytics from analytics manager if available
            if hasattr(self, 'market_analytics_manager'):
                try:
                    # Check what methods are available on analytics manager
                    if hasattr(self.market_analytics_manager, 'get_analytics_snapshot'):
                        current_analytics = self.market_analytics_manager.get_analytics_snapshot()
                        analytics_data.update(current_analytics)
                    elif hasattr(self.market_analytics_manager, 'get_current_state'):
                        current_analytics = self.market_analytics_manager.get_current_state()
                        analytics_data.update(current_analytics)
                    else:
                        logger.debug("No suitable analytics retrieval method found")
                except Exception as e:
                    logger.error(f"Error getting market analytics: {e}")
            
            # Get core gauge data from buysell_market_tracker if available
            if hasattr(self, 'buysell_market_tracker'):
                try:
                    core_gauge = self.buysell_market_tracker.get_market_gauge_data()
                    if core_gauge:
                        analytics_data['core_gauge'] = core_gauge
                except Exception as e:
                    logger.debug(f"Could not get gauge data: {e}")
            
            # Add activity level based on recent event frequency
            analytics_data['activity_level'] = self._calculate_market_activity_level()
            
            # Add metadata
            analytics_data['timestamp'] = time.time()
            analytics_data['source'] = 'market_service'
            
            return analytics_data
            
        except Exception as e:
            logger.error(f"Error getting analytics for websocket: {e}", exc_info=True)
            return {
                'session_totals': {
                    'total_highs': 0,
                    'total_lows': 0,
                    'total_events': 0
                },
                'activity_level': 'Medium',
                'error': str(e)
            }
        
    def get_session_accumulation_totals(self) -> Dict[str, Any]:
        """
        Get session accumulation totals directly.
        
        Returns:
            dict: Session totals from accumulation manager
        """
        try:
            if hasattr(self, 'session_accumulation_manager'):
                return self.session_accumulation_manager.get_session_totals()
            else:
                logger.warning("No session_accumulation_manager available")
                return {
                    'total_highs': 0,
                    'total_lows': 0,
                    'total_events': 0,
                    'active_tickers': 0,
                    'session_date': None
                }
        except Exception as e:
            logger.error(f"Error getting session totals: {e}")
            return {
                'total_highs': 0,
                'total_lows': 0,
                'total_events': 0,
                'error': str(e)
            }


    def _calculate_market_activity_level(self) -> str:
        """
        Calculate overall market activity level.
        
        Returns:
            str: Activity level (Low, Medium, High, Very High)
        """
        try:
            # Count recent events across all stocks
            current_time = time.time()
            recent_event_count = 0
            
            for stock_data in self.stock_details.values():
                # Count events in last 60 seconds
                recent_event_count += len([e for e in stock_data.events if e.time > current_time - 60])
            
            # Define thresholds (adjust based on your system)
            if recent_event_count >= 500:
                return 'Very High'
            elif recent_event_count >= 200:
                return 'High'
            elif recent_event_count >= 50:
                return 'Medium'
            else:
                return 'Low'
                
        except Exception as e:
            logger.error(f"Error calculating activity level: {e}")
            return 'Medium'