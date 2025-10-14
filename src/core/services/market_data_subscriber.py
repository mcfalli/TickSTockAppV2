"""
Market Data Redis Subscriber - Sprint 12 Phase 2
Extends existing RedisEventSubscriber for real-time market data consumption.

This service subscribes to TickStockPL market data channels and forwards
filtered updates to the dashboard via WebSocket.

PERFORMANCE TARGET: <50ms Redis processing, <100ms end-to-end delivery
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import redis
from flask_socketio import SocketIO

from src.core.services.redis_event_subscriber import RedisEventSubscriber, TickStockEvent

logger = logging.getLogger(__name__)

# New event types for market data
class MarketEventType(Enum):
    """Market data event types from TickStockPL."""
    PRICE_UPDATE = "price_update"
    OHLCV_UPDATE = "ohlcv_update"
    VOLUME_SPIKE = "volume_spike"
    MARKET_SUMMARY = "market_summary"
    SYMBOL_METADATA = "symbol_metadata"
    WATCHLIST_UPDATE = "watchlist_update"
    DASHBOARD_ALERT = "dashboard_alert"
    DASHBOARD_SUMMARY = "dashboard_summary"

@dataclass
class MarketDataEvent(TickStockEvent):
    """Enhanced event structure for market data."""
    symbol: str | None = None
    price: float | None = None
    volume: int | None = None

    def is_significant_price_change(self, threshold: float = 0.5) -> bool:
        """Check if price change is significant enough to broadcast."""
        change_percent = self.data.get('change_percent', 0)
        return abs(change_percent) >= threshold

class MarketDataSubscriber(RedisEventSubscriber):
    """
    Extended Redis subscriber for TickStockPL market data integration.
    
    Handles real-time market data streams and user-specific filtering
    for dashboard functionality with <100ms delivery targets.
    """

    def __init__(self, redis_client: redis.Redis, socketio: SocketIO, config: dict[str, Any]):
        """Initialize market data subscriber."""
        super().__init__(redis_client, socketio, config)

        # Add market data channels to existing channels
        self.market_channels = {
            'tickstock.market.prices': MarketEventType.PRICE_UPDATE,
            'tickstock.market.ohlcv': MarketEventType.OHLCV_UPDATE,
            'tickstock.market.volume': MarketEventType.VOLUME_SPIKE,
            'tickstock.market.summary': MarketEventType.MARKET_SUMMARY,
            'tickstock.market.symbols': MarketEventType.SYMBOL_METADATA,
            'tickstock.dashboard.watchlist': MarketEventType.WATCHLIST_UPDATE,
            'tickstock.dashboard.alerts': MarketEventType.DASHBOARD_ALERT,
            'tickstock.dashboard.summary': MarketEventType.DASHBOARD_SUMMARY
        }

        # Extend existing channels
        self.channels.update(self.market_channels)

        # User watchlist cache for fast filtering
        self.user_watchlists: dict[str, list[str]] = {}  # user_id -> [symbols]
        self.watchlist_cache_expiry = time.time() + 300  # 5 minute cache

        # Market data performance tracking
        self.market_stats = {
            'price_updates_processed': 0,
            'price_updates_filtered': 0,
            'price_updates_sent': 0,
            'ohlcv_updates_processed': 0,
            'watchlist_cache_hits': 0,
            'watchlist_cache_misses': 0,
            'avg_processing_time_ms': 0
        }

    def start(self) -> bool:
        """Start market data subscription service."""
        logger.info("MARKET-DATA-SUBSCRIBER: Starting enhanced market data service...")

        # Load user watchlists into cache
        self._refresh_watchlist_cache()

        # Call parent start method
        success = super().start()

        if success:
            logger.info(f"MARKET-DATA-SUBSCRIBER: Subscribed to {len(self.market_channels)} market data channels")

        return success

    def _refresh_watchlist_cache(self):
        """Refresh user watchlist cache from database."""
        try:
            start_time = time.time()

            # Query all user watchlists
            from src.core.services.user_settings_service import UserSettingsService
            settings_service = UserSettingsService()

            # Get all watchlists
            watchlists = settings_service.get_all_user_watchlists()

            self.user_watchlists = {}
            for user_id, symbols in watchlists.items():
                if symbols:  # Only cache non-empty watchlists
                    self.user_watchlists[str(user_id)] = symbols

            self.watchlist_cache_expiry = time.time() + 300  # Reset 5 minute expiry

            cache_time = (time.time() - start_time) * 1000
            logger.info(f"MARKET-DATA-SUBSCRIBER: Refreshed watchlist cache in {cache_time:.1f}ms - {len(self.user_watchlists)} users")

        except Exception as e:
            logger.error(f"MARKET-DATA-SUBSCRIBER: Failed to refresh watchlist cache: {e}")

    def _process_message(self, message: dict[str, Any]):
        """Override to add market data processing timing."""
        start_time = time.time()

        # Call parent processing
        super()._process_message(message)

        # Update performance metrics
        processing_time_ms = (time.time() - start_time) * 1000

        # Update rolling average
        current_avg = self.market_stats.get('avg_processing_time_ms', 0)
        events_processed = self.stats.get('events_processed', 1)
        self.market_stats['avg_processing_time_ms'] = (
            (current_avg * (events_processed - 1) + processing_time_ms) / events_processed
        )

        # Log slow processing
        if processing_time_ms > 50:  # Warn if over 50ms
            channel = message.get('channel', 'unknown')
            logger.warning(f"MARKET-DATA-SUBSCRIBER: Slow processing {processing_time_ms:.1f}ms for {channel}")

    def _handle_event(self, event: TickStockEvent):
        """Handle market data events with enhanced routing."""
        try:
            # Check if this is a market data event
            if event.channel in self.market_channels:
                market_event_type = self.market_channels[event.channel]

                # Create enhanced market event
                market_event = MarketDataEvent(
                    event_type=event.event_type,
                    source=event.source,
                    timestamp=event.timestamp,
                    data=event.data,
                    channel=event.channel,
                    symbol=event.data.get('symbol'),
                    price=event.data.get('price'),
                    volume=event.data.get('volume')
                )

                # Route to appropriate handler
                if market_event_type == MarketEventType.PRICE_UPDATE:
                    self._handle_price_update(market_event)
                elif market_event_type == MarketEventType.OHLCV_UPDATE:
                    self._handle_ohlcv_update(market_event)
                elif market_event_type == MarketEventType.MARKET_SUMMARY:
                    self._handle_market_summary(market_event)
                elif market_event_type == MarketEventType.WATCHLIST_UPDATE:
                    self._handle_watchlist_update(market_event)
                else:
                    # Default market data handling
                    self._handle_generic_market_event(market_event)
            else:
                # Handle existing pattern/backtest events
                super()._handle_event(event)

        except Exception as e:
            logger.error(f"MARKET-DATA-SUBSCRIBER: Error handling market event: {e}")

    def _handle_price_update(self, event: MarketDataEvent):
        """Handle real-time price updates with user filtering."""
        try:
            self.market_stats['price_updates_processed'] += 1

            symbol = event.symbol
            if not symbol:
                return

            # Check cache expiry
            if time.time() > self.watchlist_cache_expiry:
                self._refresh_watchlist_cache()

            # Get users who have this symbol in watchlist
            interested_users = self._get_users_for_symbol(symbol)

            if not interested_users:
                self.market_stats['price_updates_filtered'] += 1
                return

            # Check if price change is significant
            change_percent = event.data.get('change_percent', 0)
            if not event.is_significant_price_change(threshold=0.1):  # 0.1% threshold
                self.market_stats['price_updates_filtered'] += 1
                return

            # Broadcast to interested users
            websocket_data = {
                'type': 'price_update',
                'symbol': symbol,
                'price': event.price,
                'change': event.data.get('change', 0),
                'change_percent': change_percent,
                'volume': event.volume,
                'timestamp': event.timestamp
            }

            # Send to dashboard manager
            self.socketio.emit('dashboard_price_update', websocket_data, broadcast=True)

            self.market_stats['price_updates_sent'] += len(interested_users)
            self.stats['events_forwarded'] += 1

            logger.debug(f"MARKET-DATA-SUBSCRIBER: Price update sent - {symbol}: ${event.price} ({change_percent:+.2f}%)")

        except Exception as e:
            logger.error(f"MARKET-DATA-SUBSCRIBER: Error handling price update: {e}")

    def _handle_ohlcv_update(self, event: MarketDataEvent):
        """Handle OHLCV bar completion updates."""
        try:
            self.market_stats['ohlcv_updates_processed'] += 1

            symbol = event.symbol
            timeframe = event.data.get('timeframe', '1min')

            # Get users interested in this symbol
            interested_users = self._get_users_for_symbol(symbol)

            if interested_users:
                websocket_data = {
                    'type': 'ohlcv_update',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'ohlcv': {
                        'open': event.data.get('open'),
                        'high': event.data.get('high'),
                        'low': event.data.get('low'),
                        'close': event.data.get('close'),
                        'volume': event.data.get('volume')
                    },
                    'timestamp': event.timestamp
                }

                # Send to chart manager for real-time chart updates
                self.socketio.emit('dashboard_ohlcv_update', websocket_data, broadcast=True)
                self.stats['events_forwarded'] += 1

                logger.debug(f"MARKET-DATA-SUBSCRIBER: OHLCV update sent - {symbol} {timeframe}")

        except Exception as e:
            logger.error(f"MARKET-DATA-SUBSCRIBER: Error handling OHLCV update: {e}")

    def _handle_market_summary(self, event: MarketDataEvent):
        """Handle market-wide summary updates."""
        try:
            websocket_data = {
                'type': 'market_summary',
                'summary': {
                    'total_symbols': event.data.get('total_symbols', 0),
                    'symbols_up': event.data.get('symbols_up', 0),
                    'symbols_down': event.data.get('symbols_down', 0),
                    'total_volume': event.data.get('total_volume', 0),
                    'market_cap_change': event.data.get('market_cap_change', 0)
                },
                'timestamp': event.timestamp
            }

            # Broadcast to all dashboard users
            self.socketio.emit('dashboard_market_summary', websocket_data, broadcast=True)
            self.stats['events_forwarded'] += 1

            logger.debug("MARKET-DATA-SUBSCRIBER: Market summary update sent")

        except Exception as e:
            logger.error(f"MARKET-DATA-SUBSCRIBER: Error handling market summary: {e}")

    def _handle_watchlist_update(self, event: MarketDataEvent):
        """Handle user watchlist change notifications."""
        try:
            user_id = event.data.get('user_id')
            if user_id:
                # Invalidate cache for this user
                if str(user_id) in self.user_watchlists:
                    del self.user_watchlists[str(user_id)]

                # Force cache refresh on next price update
                if time.time() > self.watchlist_cache_expiry - 60:  # Refresh early
                    self._refresh_watchlist_cache()

        except Exception as e:
            logger.error(f"MARKET-DATA-SUBSCRIBER: Error handling watchlist update: {e}")

    def _handle_generic_market_event(self, event: MarketDataEvent):
        """Handle other market data events."""
        try:
            websocket_data = {
                'type': event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
                'event': event.to_websocket_dict()
            }

            self.socketio.emit('dashboard_market_event', websocket_data, broadcast=True)
            self.stats['events_forwarded'] += 1

        except Exception as e:
            logger.error(f"MARKET-DATA-SUBSCRIBER: Error handling generic market event: {e}")

    def _get_users_for_symbol(self, symbol: str) -> list[str]:
        """Get users who have symbol in watchlist (cached)."""
        try:
            interested_users = []

            for user_id, symbols in self.user_watchlists.items():
                if symbol in symbols:
                    interested_users.append(user_id)
                    self.market_stats['watchlist_cache_hits'] += 1
                else:
                    self.market_stats['watchlist_cache_misses'] += 1

            return interested_users

        except Exception as e:
            logger.error(f"MARKET-DATA-SUBSCRIBER: Error getting users for symbol {symbol}: {e}")
            return []

    def get_market_stats(self) -> dict[str, Any]:
        """Get market data processing statistics."""
        base_stats = self.get_stats()

        return {
            **base_stats,
            **self.market_stats,
            'watchlist_cache_size': len(self.user_watchlists),
            'cache_expiry_in': max(0, int(self.watchlist_cache_expiry - time.time()))
        }

    def get_health_status(self) -> dict[str, Any]:
        """Enhanced health status with market data metrics."""
        base_health = super().get_health_status()

        # Check market-specific health indicators
        avg_processing = self.market_stats.get('avg_processing_time_ms', 0)
        price_filter_rate = 0

        if self.market_stats.get('price_updates_processed', 0) > 0:
            price_filter_rate = (
                self.market_stats['price_updates_filtered'] /
                self.market_stats['price_updates_processed']
            )

        # Market data health status
        if avg_processing > 100:  # >100ms is concerning
            market_status = 'degraded'
            market_message = f'Slow processing: {avg_processing:.1f}ms average'
        elif price_filter_rate > 0.95:  # >95% filtering might indicate issues
            market_status = 'warning'
            market_message = f'High filter rate: {price_filter_rate:.1%} of updates filtered'
        else:
            market_status = 'healthy'
            market_message = 'Market data processing normal'

        return {
            **base_health,
            'market_data_status': market_status,
            'market_data_message': market_message,
            'market_stats': self.market_stats
        }
