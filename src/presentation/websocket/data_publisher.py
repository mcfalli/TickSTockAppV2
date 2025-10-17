"""Simplified data publisher for TickStockPL integration.

PHASE 7 CLEANUP: Simplified to Redis-based publishing with:
- Direct Redis publishing of tick data
- Simple event buffering
- Basic statistics tracking
- TickStockPL integration ready

Removed: Multi-frequency complexity, complex event management, deduplication.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import redis

from src.core.domain.market.tick import TickData

logger = logging.getLogger(__name__)

@dataclass
class PublishingResult:
    """Simple result object for publishing operations."""
    success: bool = True
    events_published: int = 0
    processing_time_ms: float = 0
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class DataPublisher:
    """Simplified data publisher for Redis-based event distribution."""

    def __init__(self, config, market_service=None, websocket_publisher=None):
        self.config = config
        self.market_service = market_service
        self.websocket_publisher = websocket_publisher

        # Redis connection for TickStockPL integration
        self.redis_client = None
        self._init_redis()

        # Simple event buffer
        self.event_buffer = []
        self.max_buffer_size = config.get('PUBLISHER_BUFFER_SIZE', 1000)

        # Basic statistics
        self.events_published = 0
        self.events_buffered = 0
        self.last_stats_log = time.time()

        logger.info("DATA-PUBLISHER: Simplified publisher initialized with Redis")

    def _init_redis(self):
        """Initialize Redis connection for TickStockPL integration."""
        # Check if Redis is configured
        redis_url = self.config.get('REDIS_URL')
        if not redis_url or redis_url.strip() == '':
            logger.info("DATA-PUBLISHER: No Redis URL configured, skipping Redis initialization")
            self.redis_client = None
            return

        redis_host = self.config.get('REDIS_HOST', 'localhost')
        redis_port = int(self.config.get('REDIS_PORT', 6379))
        redis_db = int(self.config.get('REDIS_DB', 0))

        logger.info(f"DATA-PUBLISHER: Attempting to connect to Redis at {redis_host}:{redis_port}")

        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"DATA-PUBLISHER: Redis connected successfully to {redis_host}:{redis_port}")
        except Exception as e:
            logger.warning(f"DATA-PUBLISHER: Redis connection failed: {e}")
            self.redis_client = None

    def publish_tick_data(self, tick_data: TickData) -> PublishingResult:
        """Publish tick data to Redis and WebSocket subscribers."""
        start_time = time.time()
        result = PublishingResult()

        try:
            # Buffer the event
            self._buffer_event(tick_data)

            # Publish to Redis for TickStockPL
            if self.redis_client:
                self._publish_to_redis(tick_data)

            # Publish to WebSocket subscribers
            if self.websocket_publisher:
                self._publish_to_websocket(tick_data)

            result.events_published = 1
            self.events_published += 1

            # Log stats periodically
            self._log_stats_if_needed()

        except Exception as e:
            logger.error(f"DATA-PUBLISHER: Error publishing tick data: {e}")
            result.success = False

        result.processing_time_ms = (time.time() - start_time) * 1000
        return result

    def _buffer_event(self, tick_data: TickData):
        """Add event to buffer with overflow protection."""
        self.event_buffer.append(tick_data)
        self.events_buffered += 1

        # Prevent buffer overflow
        if len(self.event_buffer) > self.max_buffer_size:
            self.event_buffer.pop(0)
            # Buffer overflow is normal operation - no logging needed

    def _publish_to_redis(self, tick_data: TickData):
        """Publish tick data to Redis for TickStockPL consumption."""
        try:
            # Create Redis message
            redis_message = {
                'event_type': 'tick_data',
                'ticker': tick_data.ticker,
                'price': tick_data.price,
                'volume': tick_data.volume,
                'timestamp': tick_data.timestamp,
                'source': tick_data.source,
                'market_status': tick_data.market_status
            }

            # Publish to Redis channel
            channel = f"tickstock.ticks.{tick_data.ticker}"
            self.redis_client.publish(channel, json.dumps(redis_message))

            # Also publish to general channel for TickStockPL
            self.redis_client.publish('tickstock.all_ticks', json.dumps(redis_message))

            #logger.debug(f"DATA-PUBLISHER: Published {tick_data.ticker} to Redis")

        except Exception as e:
            logger.error(f"DATA-PUBLISHER: Redis publish error: {e}")

    def _publish_to_websocket(self, tick_data: TickData):
        """Publish to WebSocket subscribers."""
        try:
            if hasattr(self.websocket_publisher, 'emit_tick_data'):
                self.websocket_publisher.emit_tick_data(tick_data)
            else:
                logger.debug("DATA-PUBLISHER: No WebSocket publisher available")
        except Exception as e:
            logger.error(f"DATA-PUBLISHER: WebSocket publish error: {e}")

    def _log_stats_if_needed(self):
        """Log statistics periodically."""
        if time.time() - self.last_stats_log > 30:  # Every 30 seconds
            logger.info(
                f"DATA-PUBLISHER: Published {self.events_published} events, "
                f"Buffered {self.events_buffered}, Buffer size: {len(self.event_buffer)}"
            )
            self.last_stats_log = time.time()

    def get_buffered_events(self) -> list[TickData]:
        """Get current buffered events (for pull model)."""
        return self.event_buffer.copy()

    def clear_buffer(self):
        """Clear the event buffer."""
        cleared_count = len(self.event_buffer)
        self.event_buffer.clear()
        logger.debug(f"DATA-PUBLISHER: Cleared {cleared_count} events from buffer")
        return cleared_count

    def get_stats(self) -> dict[str, Any]:
        """Get publisher statistics."""
        return {
            'events_published': self.events_published,
            'events_buffered': self.events_buffered,
            'current_buffer_size': len(self.event_buffer),
            'max_buffer_size': self.max_buffer_size,
            'redis_connected': self.redis_client is not None
        }
