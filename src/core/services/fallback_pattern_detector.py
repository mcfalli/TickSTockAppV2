"""
Fallback Pattern Detection Service
Provides basic pattern detection when TickStockPL is unavailable.

This service implements essential pattern detection algorithms locally
to ensure continuous operation when the main TickStockPL system is offline.

Author: Redis Integration Specialist
Date: 2025-09-12
Sprint: 25 - Redis Integration Repair
"""

import json
import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import redis
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

class PatternType(Enum):
    """Basic pattern types for fallback detection."""
    DOJI = "Doji"
    HAMMER = "Hammer"
    SHOOTING_STAR = "Shooting_Star"
    ENGULFING_BULL = "Engulfing_Bull"
    ENGULFING_BEAR = "Engulfing_Bear"
    HIGH_VOLUME_SURGE = "High_Volume_Surge"
    PRICE_GAP = "Price_Gap"

@dataclass
class TickData:
    """Market tick data structure."""
    symbol: str
    price: float
    volume: int
    timestamp: float
    high: float | None = None
    low: float | None = None
    open: float | None = None

@dataclass
class PatternDetection:
    """Pattern detection result."""
    pattern: PatternType
    symbol: str
    confidence: float
    timestamp: float
    price: float
    volume: int
    direction: str
    metadata: dict[str, Any]

class FallbackPatternDetector:
    """
    Fallback pattern detection service for when TickStockPL is offline.
    
    Implements basic candlestick and volume pattern detection using
    market data from the existing TickStock processing pipeline.
    """

    def __init__(self, redis_client: redis.Redis, socketio: SocketIO,
                 config: dict[str, Any]):
        """Initialize fallback pattern detector."""
        self.redis_client = redis_client
        self.socketio = socketio
        self.config = config

        # Pattern detection state
        self.is_active = False
        self.detection_thread = None

        # Market data buffer (symbol -> list of recent ticks)
        self.market_data_buffer: dict[str, list[TickData]] = {}
        self.max_buffer_size = 100  # Keep last 100 ticks per symbol

        # Pattern detection queue
        self.detection_queue = queue.Queue(maxsize=1000)

        # Detection statistics
        self.stats = {
            'patterns_detected': 0,
            'symbols_monitored': 0,
            'detection_latency_ms': 0.0,
            'start_time': None,
            'last_detection': None
        }

        # TickStockPL fallback mode flag
        self.tickstock_pl_available = False
        self.last_pl_heartbeat = 0

        logger.info("FALLBACK-DETECTOR: Initialized fallback pattern detector")

    def start(self) -> bool:
        """Start the fallback pattern detection service."""
        if self.is_active:
            logger.warning("FALLBACK-DETECTOR: Already active")
            return True

        try:
            self.is_active = True
            self.stats['start_time'] = time.time()

            # Start pattern detection thread
            self.detection_thread = threading.Thread(
                target=self._detection_loop,
                name="FallbackPatternDetector",
                daemon=True
            )
            self.detection_thread.start()

            # Start TickStockPL monitoring
            self._start_pl_monitoring()

            logger.info("FALLBACK-DETECTOR: Service started successfully")
            return True

        except Exception as e:
            logger.error(f"FALLBACK-DETECTOR: Failed to start: {e}")
            self.is_active = False
            return False

    def stop(self):
        """Stop the fallback pattern detection service."""
        if not self.is_active:
            return

        logger.info("FALLBACK-DETECTOR: Stopping service...")
        self.is_active = False

        # Wait for threads to complete
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=5)

        logger.info("FALLBACK-DETECTOR: Service stopped")

    def add_market_tick(self, symbol: str, price: float, volume: int,
                       timestamp: float | None = None):
        """Add new market tick for pattern analysis."""
        if not self.is_active:
            return

        if timestamp is None:
            timestamp = time.time()

        tick = TickData(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=timestamp
        )

        # Add to buffer
        if symbol not in self.market_data_buffer:
            self.market_data_buffer[symbol] = []

        buffer = self.market_data_buffer[symbol]
        buffer.append(tick)

        # Maintain buffer size
        if len(buffer) > self.max_buffer_size:
            buffer.pop(0)

        # Queue for pattern detection
        try:
            self.detection_queue.put_nowait(tick)
        except queue.Full:
            logger.warning("FALLBACK-DETECTOR: Detection queue full, dropping tick")

    def _detection_loop(self):
        """Main pattern detection loop."""
        logger.info("FALLBACK-DETECTOR: Starting detection loop")

        while self.is_active:
            try:
                # Check if TickStockPL is back online
                self._check_tickstock_pl_status()

                # Skip detection if TickStockPL is available
                if self.tickstock_pl_available:
                    time.sleep(1)
                    continue

                # Get tick from queue
                try:
                    tick = self.detection_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                # Run pattern detection
                start_time = time.time()
                patterns = self._detect_patterns(tick)
                detection_time = (time.time() - start_time) * 1000

                # Update statistics
                self.stats['detection_latency_ms'] = (
                    self.stats['detection_latency_ms'] * 0.9 + detection_time * 0.1
                )

                # Publish detected patterns
                for pattern in patterns:
                    self._publish_pattern(pattern)
                    self.stats['patterns_detected'] += 1
                    self.stats['last_detection'] = time.time()

                self.detection_queue.task_done()

            except Exception as e:
                logger.error(f"FALLBACK-DETECTOR: Error in detection loop: {e}")
                time.sleep(1)

        logger.info("FALLBACK-DETECTOR: Exited detection loop")

    def _detect_patterns(self, tick: TickData) -> list[PatternDetection]:
        """Detect patterns for the given tick."""
        patterns = []

        if tick.symbol not in self.market_data_buffer:
            return patterns

        buffer = self.market_data_buffer[tick.symbol]
        if len(buffer) < 5:  # Need minimum history
            return patterns

        # Get recent price action
        recent_ticks = buffer[-10:]  # Last 10 ticks
        current_tick = recent_ticks[-1]

        # Pattern 1: High Volume Surge
        volume_pattern = self._detect_high_volume_surge(recent_ticks)
        if volume_pattern:
            patterns.append(volume_pattern)

        # Pattern 2: Simple Doji (price oscillation)
        doji_pattern = self._detect_simple_doji(recent_ticks)
        if doji_pattern:
            patterns.append(doji_pattern)

        # Pattern 3: Price Gap
        gap_pattern = self._detect_price_gap(recent_ticks)
        if gap_pattern:
            patterns.append(gap_pattern)

        return patterns

    def _detect_high_volume_surge(self, ticks: list[TickData]) -> PatternDetection | None:
        """Detect high volume surge pattern."""
        if len(ticks) < 5:
            return None

        current_tick = ticks[-1]
        avg_volume = sum(t.volume for t in ticks[:-1]) / len(ticks[:-1])

        # Volume surge threshold (3x average)
        if current_tick.volume > avg_volume * 3 and avg_volume > 100:
            # Calculate price change from previous tick
            price_change = 0.0
            if len(ticks) >= 2:
                prev_price = ticks[-2].price
                price_change = ((current_tick.price - prev_price) / prev_price) * 100

            return PatternDetection(
                pattern=PatternType.HIGH_VOLUME_SURGE,
                symbol=current_tick.symbol,
                confidence=0.75,
                timestamp=current_tick.timestamp,
                price=current_tick.price,
                volume=current_tick.volume,
                direction="neutral",
                metadata={
                    "avg_volume": avg_volume,
                    "volume_ratio": current_tick.volume / avg_volume,
                    "price_change": price_change,
                    "source": "fallback_detector"
                }
            )

        return None

    def _detect_simple_doji(self, ticks: list[TickData]) -> PatternDetection | None:
        """Detect simple doji-like pattern (price oscillation)."""
        if len(ticks) < 7:
            return None

        # Look for price oscillation pattern
        recent_prices = [t.price for t in ticks[-7:]]
        price_range = max(recent_prices) - min(recent_prices)
        avg_price = sum(recent_prices) / len(recent_prices)

        current_tick = ticks[-1]

        # Doji-like: price near middle of recent range
        middle_threshold = 0.3  # Within 30% of middle
        price_middle_distance = abs(current_tick.price - avg_price) / price_range

        if price_range > 0 and price_middle_distance < middle_threshold:
            # Calculate price change from first to last price in range
            first_price = recent_prices[0]
            price_change = ((current_tick.price - first_price) / first_price) * 100

            return PatternDetection(
                pattern=PatternType.DOJI,
                symbol=current_tick.symbol,
                confidence=0.6,
                timestamp=current_tick.timestamp,
                price=current_tick.price,
                volume=current_tick.volume,
                direction="reversal",
                metadata={
                    "price_range": price_range,
                    "avg_price": avg_price,
                    "middle_distance": price_middle_distance,
                    "price_change": price_change,
                    "source": "fallback_detector"
                }
            )

        return None

    def _detect_price_gap(self, ticks: list[TickData]) -> PatternDetection | None:
        """Detect significant price gaps."""
        if len(ticks) < 3:
            return None

        current_tick = ticks[-1]
        prev_tick = ticks[-2]

        # Calculate price gap percentage
        price_change = abs(current_tick.price - prev_tick.price)
        gap_percentage = (price_change / prev_tick.price) * 100

        # Gap threshold (2% or more)
        if gap_percentage > 2.0:
            direction = "bullish" if current_tick.price > prev_tick.price else "bearish"

            return PatternDetection(
                pattern=PatternType.PRICE_GAP,
                symbol=current_tick.symbol,
                confidence=0.8,
                timestamp=current_tick.timestamp,
                price=current_tick.price,
                volume=current_tick.volume,
                direction=direction,
                metadata={
                    "gap_percentage": gap_percentage,
                    "price_change": price_change,
                    "prev_price": prev_tick.price,
                    "source": "fallback_detector"
                }
            )

        return None

    def _publish_pattern(self, pattern: PatternDetection):
        """Publish detected pattern via Redis and WebSocket."""
        try:
            # Create pattern event message in correct nested structure
            current_timestamp = pattern.timestamp
            pattern_event = {
                "event_type": "pattern_detected",
                "source": "fallback_detector",
                "timestamp": current_timestamp,
                "data": {
                    "symbol": pattern.symbol,
                    "pattern": pattern.pattern.value,
                    "confidence": pattern.confidence,
                    "current_price": pattern.price,
                    "price_change": pattern.metadata.get('price_change', 0.0),
                    "timestamp": current_timestamp,
                    "expires_at": current_timestamp + (3 * 24 * 60 * 60),  # 3 days
                    "indicators": {
                        "relative_strength": pattern.metadata.get('relative_strength', 1.0),
                        "relative_volume": pattern.metadata.get('volume_ratio', 1.0),
                        "volume": pattern.volume
                    },
                    "source": "fallback"  # Data source tier
                }
            }

            # Publish to Redis channel (same as TickStockPL)
            message = json.dumps(pattern_event)
            self.redis_client.publish('tickstock.events.patterns', message)

            # Direct WebSocket broadcast (backup)
            websocket_data = {
                'type': 'pattern_alert',
                'event': pattern_event
            }

            self.socketio.emit('pattern_alert', websocket_data, namespace='/')

            logger.info(f"FALLBACK-DETECTOR: Published {pattern.pattern.value} on {pattern.symbol} (confidence: {pattern.confidence:.2f})")

        except Exception as e:
            logger.error(f"FALLBACK-DETECTOR: Failed to publish pattern: {e}")

    def _start_pl_monitoring(self):
        """Start monitoring TickStockPL availability."""
        def monitor():
            while self.is_active:
                try:
                    # Check for TickStockPL heartbeat
                    heartbeat = self.redis_client.get('tickstock:producer:heartbeat')
                    if heartbeat:
                        self.last_pl_heartbeat = float(heartbeat)

                    time.sleep(5)  # Check every 5 seconds

                except Exception as e:
                    logger.debug(f"FALLBACK-DETECTOR: PL monitoring error: {e}")
                    time.sleep(5)

        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

    def _check_tickstock_pl_status(self) -> bool:
        """Check if TickStockPL is available."""
        current_time = time.time()

        # Consider TickStockPL available if heartbeat is recent (within 30 seconds)
        pl_available = (current_time - self.last_pl_heartbeat) < 30

        if pl_available != self.tickstock_pl_available:
            if pl_available:
                logger.info("FALLBACK-DETECTOR: TickStockPL detected as ONLINE - switching to passive mode")
            else:
                logger.info("FALLBACK-DETECTOR: TickStockPL detected as OFFLINE - activating fallback detection")

        self.tickstock_pl_available = pl_available
        return pl_available

    def get_stats(self) -> dict[str, Any]:
        """Get detector statistics."""
        runtime = time.time() - (self.stats['start_time'] or time.time())

        return {
            **self.stats,
            'runtime_seconds': round(runtime, 1),
            'is_active': self.is_active,
            'tickstock_pl_available': self.tickstock_pl_available,
            'symbols_monitored': len(self.market_data_buffer),
            'buffer_sizes': {symbol: len(buffer) for symbol, buffer in self.market_data_buffer.items()},
            'queue_size': self.detection_queue.qsize()
        }

    def get_health_status(self) -> dict[str, Any]:
        """Get health status for monitoring."""
        stats = self.get_stats()

        if not self.is_active:
            status = 'inactive'
            message = 'Fallback detector not running'
        elif self.tickstock_pl_available:
            status = 'standby'
            message = 'TickStockPL available - fallback detector on standby'
        elif stats['patterns_detected'] == 0 and runtime > 300:
            status = 'warning'
            message = 'No patterns detected in 5 minutes'
        else:
            status = 'active'
            message = 'Fallback detection active'

        return {
            'status': status,
            'message': message,
            'stats': stats,
            'last_check': time.time()
        }
