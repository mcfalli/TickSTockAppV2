"""Simplified market data service for TickStockPL integration.

PHASE 8 CLEANUP: Simplified to essential data processing with:
- Basic tick data ingestion
- Simple data forwarding to publishers
- Redis integration for TickStockPL
- Essential service lifecycle management

Removed: Complex orchestration, analytics coordination, worker pools, universe management.
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from src.core.domain.market.tick import TickData
from src.infrastructure.data_sources.adapters.realtime_adapter import (
    RealTimeDataAdapter,
    SyntheticDataAdapter,
)

logger = logging.getLogger(__name__)

@dataclass
class ServiceStats:
    """Simple service statistics."""
    ticks_processed: int = 0
    events_published: int = 0
    start_time: float = None
    last_tick_time: float = None

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time.time()

class MarketDataService:
    """Simplified market data service for basic tick processing."""

    def __init__(self, config, socketio=None):
        self.config = config
        self.socketio = socketio

        # Service state
        self.running = False
        self.stats = ServiceStats()

        # Core components
        # DataPublisher removed in Sprint 54 - frontend polls REST endpoint instead
        self.data_adapter = None

        # Thread management
        self._service_thread = None
        self._shutdown_event = threading.Event()

        logger.info("MARKET-DATA-SERVICE: Simplified service initialized")

    def start(self) -> bool:
        """Start the market data service."""
        try:
            if self.running:
                logger.warning("MARKET-DATA-SERVICE: Service already running")
                return True

            logger.info("MARKET-DATA-SERVICE: Starting service...")

            # Initialize data adapter
            self._init_data_adapter()

            # Start service thread
            self._service_thread = threading.Thread(target=self._service_loop, daemon=True)
            self._service_thread.start()

            self.running = True
            logger.info("MARKET-DATA-SERVICE: Service started successfully")
            return True

        except Exception as e:
            logger.error(f"MARKET-DATA-SERVICE: Failed to start service: {e}")
            return False

    def stop(self):
        """Stop the market data service."""
        if not self.running:
            return

        logger.info("MARKET-DATA-SERVICE: Stopping service...")

        self.running = False
        self._shutdown_event.set()

        # Disconnect data adapter
        if self.data_adapter:
            self.data_adapter.disconnect()

        # Wait for service thread to finish
        if self._service_thread and self._service_thread.is_alive():
            self._service_thread.join(timeout=5.0)

        logger.info("MARKET-DATA-SERVICE: Service stopped")

    def _init_data_adapter(self):
        """Initialize the appropriate data adapter."""
        use_synthetic = self.config.get('USE_SYNTHETIC_DATA', False)
        use_massive = self.config.get('USE_MASSIVE_API', False)

        if use_massive and self.config.get('MASSIVE_API_KEY'):
            logger.info("MARKET-DATA-SERVICE: Initializing Massive WebSocket adapter")
            self.data_adapter = RealTimeDataAdapter(
                config=self.config,
                tick_callback=self._handle_tick_data,
                status_callback=self._handle_status_update
            )
        else:
            logger.info("MARKET-DATA-SERVICE: Initializing synthetic data adapter")
            self.data_adapter = SyntheticDataAdapter(
                config=self.config,
                tick_callback=self._handle_tick_data,
                status_callback=self._handle_status_update
            )

    def _service_loop(self):
        """Main service loop."""
        try:
            # Get universe of tickers to monitor
            universe = self._get_universe()

            # Connect to data source
            if self.data_adapter and self.data_adapter.connect(universe):
                logger.info(f"MARKET-DATA-SERVICE: Connected to data source with {len(universe)} tickers")

                # Keep service running
                while self.running and not self._shutdown_event.is_set():
                    time.sleep(1.0)

                    # Log stats periodically
                    self._log_stats_if_needed()
            else:
                logger.error("MARKET-DATA-SERVICE: Failed to connect to data source")

        except Exception as e:
            logger.error(f"MARKET-DATA-SERVICE: Service loop error: {e}")
        finally:
            self.running = False

    def _get_universe(self) -> list[str]:
        """Get the universe of tickers to monitor from cache configuration."""
        # Default fallback universe
        default_universe = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NFLX', 'META', 'NVDA']

        try:
            # Get universe key from configuration
            universe_key = self.config.get('SYMBOL_UNIVERSE_KEY', 'market_leaders:top_50')
            logger.info(f"MARKET-DATA-SERVICE: Loading universe from key: {universe_key}")

            # Sprint 61: Use RelationshipCache instead of CacheControl
            # Supports multi-universe join (e.g., 'sp500:nasdaq100')
            from src.core.services.relationship_cache import get_relationship_cache
            cache = get_relationship_cache()

            # Get tickers from cache (supports multi-universe join with colon separator)
            universe_tickers = cache.get_universe_symbols(universe_key)

            if universe_tickers and len(universe_tickers) > 0:
                logger.info(f"MARKET-DATA-SERVICE: Using universe '{universe_key}' with {len(universe_tickers)} tickers: {', '.join(universe_tickers[:10])}{'...' if len(universe_tickers) > 10 else ''}")
                return universe_tickers
            logger.warning(f"MARKET-DATA-SERVICE: Universe key '{universe_key}' not found or empty, using default")

        except Exception as e:
            logger.error(f"MARKET-DATA-SERVICE: Error loading universe from cache: {e}")

        # Fallback to default universe
        logger.info(f"MARKET-DATA-SERVICE: Using default universe with {len(default_universe)} tickers")
        return default_universe

    def _handle_tick_data(self, tick_data: TickData):
        """Handle incoming tick data - simplified for standalone AppV2.
        
        Sprint 54: WebSocket Processing Simplification
        - Removed ALL TickStockPL integration (Redis publishing TO TickStockPL)
        - Removed DataPublisher for tick broadcasting
        - Added direct database persistence to ohlcv_1min table
        - PRESERVED FallbackPatternDetector for local pattern detection
        """
        try:
            # STAGE 1: Update statistics (PRESERVED)
            self.stats.ticks_processed += 1
            self.stats.last_tick_time = time.time()

            # STAGE 2: Feed to fallback pattern detector (PRESERVED - Decision 2)
            # Import here to avoid circular import
            from src.app import fallback_pattern_detector
            if fallback_pattern_detector and fallback_pattern_detector.is_active:
                fallback_pattern_detector.add_market_tick(
                    tick_data.ticker,
                    tick_data.price,
                    tick_data.volume or 0,
                    tick_data.timestamp
                )

            # STAGE 3: Write to database (NEW - Sprint 54)
            try:
                # Extract OHLCV fields from TickData
                symbol = tick_data.ticker

                # Convert Unix timestamp to timezone-aware datetime
                timestamp = datetime.fromtimestamp(tick_data.timestamp, tz=UTC)

                # Use tick-level OHLCV if available (Massive 'A' events), else fall back to current price
                open_price = getattr(tick_data, 'tick_open', None) or tick_data.price
                high_price = getattr(tick_data, 'tick_high', None) or tick_data.price
                low_price = getattr(tick_data, 'tick_low', None) or tick_data.price
                close_price = getattr(tick_data, 'tick_close', None) or tick_data.price
                volume = getattr(tick_data, 'tick_volume', None) or tick_data.volume or 0

                # Lazy initialize database connection
                if not hasattr(self, '_db'):
                    from src.core.services.config_manager import get_config
                    from src.infrastructure.database.tickstock_db import TickStockDatabase
                    self._db = TickStockDatabase(get_config())

                # Write to database (async, non-blocking)
                success = self._db.write_ohlcv_1min(
                    symbol=symbol,
                    timestamp=timestamp,
                    open_price=Decimal(str(open_price)),
                    high_price=Decimal(str(high_price)),
                    low_price=Decimal(str(low_price)),
                    close_price=Decimal(str(close_price)),
                    volume=int(volume)
                )

                if success:
                    # Track successful database writes
                    if not hasattr(self.stats, 'database_writes_completed'):
                        self.stats.database_writes_completed = 0
                    self.stats.database_writes_completed += 1

                    # Sprint 75 Phase 1: Trigger pattern/indicator analysis
                    self._trigger_bar_analysis_async(symbol, timestamp)
                else:
                    logger.warning(f"MARKET-DATA-SERVICE: Database write failed for {symbol} at {timestamp}")

            except Exception as e:
                logger.error(f"MARKET-DATA-SERVICE: Database write error for {tick_data.ticker}: {e}")

            # STAGE 4: Debug logging (PRESERVED)
            if self.stats.ticks_processed <= 10:
                logger.info(
                    f"MARKET-DATA-SERVICE: Processed tick #{self.stats.ticks_processed}: "
                    f"{tick_data.ticker} @ ${tick_data.price}"
                )

        except Exception as e:
            logger.error(f"MARKET-DATA-SERVICE: Error handling tick data: {e}")

    def _trigger_bar_analysis_async(self, symbol: str, timestamp: datetime):
        """
        Trigger pattern/indicator analysis for newly created OHLCV bar.

        Sprint 75 Phase 1: Real-Time WebSocket Integration
        Runs in background thread to avoid blocking tick ingestion.

        Performance target: <100ms total (non-blocking)

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            timestamp: Bar timestamp (timezone-aware datetime)
        """
        def run_analysis():
            try:
                # Import here to avoid circular dependency
                from src.analysis.services.analysis_service import AnalysisService
                from src.analysis.data.ohlcv_data_service import OHLCVDataService
                from src.api.rest.admin_process_analysis import (
                    _persist_pattern_results,
                    _persist_indicator_results,
                    _cleanup_old_patterns
                )

                # Fetch last 200 DAILY bars (sufficient for all patterns/indicators)
                # Sprint 76: Fixed to use 'daily' data (was '1min' causing incorrect SMA values)
                ohlcv_service = OHLCVDataService()
                data = ohlcv_service.get_ohlcv_data(
                    symbol=symbol,
                    timeframe='daily',
                    limit=200
                )

                if data is None or len(data) == 0:
                    logger.debug(f"ANALYSIS: No OHLCV data for {symbol} - skipping analysis")
                    return

                # Reset index to make timestamp a column (patterns require it)
                data = data.reset_index()
                # Ensure column is named 'timestamp' (may be 'date' from daily tables)
                if 'date' in data.columns:
                    data = data.rename(columns={'date': 'timestamp'})

                # Run analysis with all available patterns/indicators
                # Note: Use 'daily' for loading patterns/indicators (registered for 'daily' timeframe)
                # Candlestick patterns are timeframe-agnostic and work on any OHLCV data
                analysis_service = AnalysisService()
                results = analysis_service.analyze_symbol(
                    symbol=symbol,
                    data=data,
                    timeframe='daily',  # Load patterns/indicators registered for 'daily'
                    indicators=None,  # Use all available (18 indicators)
                    patterns=None,    # Use all available (8 patterns)
                    calculate_all=True
                )

                # Persist results with 'daily' timeframe (matches data source)
                # Sprint 76: Changed from '1min' to 'daily' to match fetched data
                _persist_pattern_results(symbol, results['patterns'], 'daily')
                _persist_indicator_results(symbol, results['indicators'], 'daily')

                # Cleanup old patterns (48-hour retention from Sprint 74)
                _cleanup_old_patterns()

                # Publish Redis event for UI updates
                try:
                    from src.infrastructure.redis.redis_connection_manager import get_redis_manager
                    redis_manager = get_redis_manager()
                    if redis_manager:
                        event_data = {
                            'symbol': symbol,
                            'timestamp': timestamp.isoformat(),
                            'timeframe': '1min',
                            'patterns_detected': len([p for p in results['patterns'].values() if p['detected']]),
                            'indicators_calculated': len(results['indicators'])
                        }
                        redis_manager.publish_message('tickstock:events:analysis_complete', event_data)
                except Exception as e:
                    logger.warning(f"ANALYSIS: Redis event publish failed: {e}")

                logger.info(
                    f"ANALYSIS: Bar analysis complete for {symbol} at {timestamp}: "
                    f"{len(results['patterns'])} patterns, {len(results['indicators'])} indicators"
                )

            except Exception as e:
                logger.error(f"ANALYSIS: Bar analysis failed for {symbol} at {timestamp}: {e}", exc_info=True)

        # Spawn background thread (non-blocking)
        thread = threading.Thread(
            target=run_analysis,
            daemon=True,
            name=f"BarAnalysis-{symbol}-{timestamp.strftime('%H%M%S')}"
        )
        thread.start()

    def _handle_status_update(self, status: str, data: dict[str, Any] = None):
        """Handle status updates from data sources."""
        #logger.info(f"MARKET-DATA-SERVICE: Status update: {status}")
        if data:
            logger.debug(f"MARKET-DATA-SERVICE: Status data: {data}")

    def _log_stats_if_needed(self):
        """Log service statistics periodically."""
        if self.stats.ticks_processed > 0 and self.stats.ticks_processed % 50 == 0:
            uptime = time.time() - self.stats.start_time
            tick_rate = self.stats.ticks_processed / uptime if uptime > 0 else 0

            logger.info(
                f"MARKET-DATA-SERVICE: Processed {self.stats.ticks_processed} ticks, "
                f"Published {self.stats.events_published} events, "
                f"Rate: {tick_rate:.1f} ticks/sec"
            )

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        uptime = time.time() - self.stats.start_time if self.stats.start_time else 0

        base_stats = {
            'running': self.running,
            'ticks_processed': self.stats.ticks_processed,
            'events_published': self.stats.events_published,
            'uptime_seconds': uptime,
            'tick_rate': self.stats.ticks_processed / uptime if uptime > 0 else 0,
            'last_tick_time': self.stats.last_tick_time
        }

        # Add publisher stats if available
        if self.data_publisher:
            publisher_stats = self.data_publisher.get_stats()
            base_stats.update({f'publisher_{k}': v for k, v in publisher_stats.items()})

        if self.websocket_publisher:
            ws_stats = self.websocket_publisher.get_stats()
            base_stats.update({f'websocket_{k}': v for k, v in ws_stats.items()})

        return base_stats

    def is_running(self) -> bool:
        """Check if service is running."""
        return self.running

    def get_health_status(self) -> dict[str, Any]:
        """Get health status for monitoring."""
        health_status = {
            'service_running': self.running,
            'ticks_processed': self.stats.ticks_processed,
            'last_tick_age_seconds': time.time() - self.stats.last_tick_time if self.stats.last_tick_time else None,
            'data_adapter_connected': self.data_adapter is not None,
            'redis_connected': self.data_publisher.redis_client is not None if self.data_publisher else False
        }

        return health_status
