"""Simplified market data service for TickStockPL integration.

PHASE 8 CLEANUP: Simplified to essential data processing with:
- Basic tick data ingestion
- Simple data forwarding to publishers
- Redis integration for TickStockPL
- Essential service lifecycle management

Removed: Complex orchestration, analytics coordination, worker pools, universe management.
"""

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

from src.core.domain.market.tick import TickData
from src.infrastructure.data_sources.adapters.realtime_adapter import (
    RealTimeDataAdapter,
    SyntheticDataAdapter,
)
from src.presentation.websocket.data_publisher import DataPublisher
from src.presentation.websocket.publisher import WebSocketPublisher

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
        self.data_publisher = DataPublisher(config, self)
        self.websocket_publisher = WebSocketPublisher(config, socketio, self) if socketio else None
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
        use_polygon = self.config.get('USE_POLYGON_API', False)

        if use_polygon and self.config.get('MASSIVE_API_KEY'):
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

            # Import here to avoid circular imports
            from src.infrastructure.cache.cache_control import CacheControl
            cache = CacheControl()

            # Get tickers from cache
            universe_tickers = cache.get_universe_tickers(universe_key)

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
        """Handle incoming tick data."""
        try:
            # Update statistics
            self.stats.ticks_processed += 1
            self.stats.last_tick_time = time.time()

            # Feed tick data to fallback pattern detector for analysis
            # Import here to avoid circular import
            from src.app import fallback_pattern_detector
            if fallback_pattern_detector and fallback_pattern_detector.is_active:
                fallback_pattern_detector.add_market_tick(
                    tick_data.ticker,
                    tick_data.price,
                    tick_data.volume or 0,
                    tick_data.timestamp
                )

            # Publish tick data
            if self.data_publisher:
                result = self.data_publisher.publish_tick_data(tick_data)
                if result.success:
                    self.stats.events_published += 1

            # Publish raw tick data to Redis for TickStockPL processing
            if self.data_publisher and self.data_publisher.redis_client:
                try:
                    raw_data = {
                        'ticker': tick_data.ticker,
                        'price': tick_data.price,
                        'volume': tick_data.volume,
                        'timestamp': tick_data.timestamp,
                        'event_type': tick_data.event_type,
                        'source': tick_data.source,
                        'tick_open': getattr(tick_data, 'tick_open', None),
                        'tick_high': getattr(tick_data, 'tick_high', None),
                        'tick_low': getattr(tick_data, 'tick_low', None),
                        'tick_close': getattr(tick_data, 'tick_close', None),
                        'tick_volume': getattr(tick_data, 'tick_volume', None),
                        'tick_vwap': getattr(tick_data, 'tick_vwap', None),
                        'bid': getattr(tick_data, 'bid', None),
                        'ask': getattr(tick_data, 'ask', None)
                    }
                    self.data_publisher.redis_client.publish('tickstock.data.raw', json.dumps(raw_data))
                except Exception as e:
                    logger.error(f"MARKET-DATA-SERVICE: Failed to publish raw data to Redis: {e}")

            # Forward tick to TickStockPL streaming service (Sprint 40)
            if self.data_publisher and self.data_publisher.redis_client:
                try:
                    # Format tick data for TickStockPL streaming service
                    market_tick = {
                        'type': 'market_tick',
                        'symbol': tick_data.ticker,
                        'price': tick_data.price,
                        'volume': tick_data.volume or 0,
                        'timestamp': tick_data.timestamp,
                        'source': 'polygon'
                    }

                    # Publish to TickStockPL streaming channel
                    self.data_publisher.redis_client.publish(
                        'tickstock:market:ticks',
                        json.dumps(market_tick)
                    )

                    # Log every 100 forwarded ticks
                    if not hasattr(self, '_forwarded_tick_count'):
                        self._forwarded_tick_count = 0
                    self._forwarded_tick_count += 1

                    if self._forwarded_tick_count % 100 == 0:
                        logger.debug(f"MARKET-DATA-SERVICE: Forwarded {self._forwarded_tick_count} ticks to TickStockPL streaming")

                except Exception as e:
                    logger.error(f"MARKET-DATA-SERVICE: Failed to forward tick to TickStockPL: {e}")

            # Log first few ticks for debugging
            if self.stats.ticks_processed <= 10:
                logger.info(f"MARKET-DATA-SERVICE: Processed tick #{self.stats.ticks_processed}: {tick_data.ticker} @ ${tick_data.price}")

        except Exception as e:
            logger.error(f"MARKET-DATA-SERVICE: Error handling tick data: {e}")

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
