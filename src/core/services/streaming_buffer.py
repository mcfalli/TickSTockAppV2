"""
Streaming Buffer Service for Smart Event Batching
Sprint 33 Phase 5: Real-time streaming integration

Buffers high-frequency streaming events (patterns, indicators) to prevent UI overload
while ensuring critical alerts are sent immediately.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

@dataclass
class BufferedEvent:
    """Container for buffered events with metadata."""
    event_type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    priority: int = 0  # 0=normal, 1=high, 2=critical

class StreamingBuffer:
    """
    Smart buffering for high-frequency streaming events.

    Batches pattern and indicator events while sending critical alerts immediately.
    Prevents browser overload during high-volume trading periods.
    """

    def __init__(self, socketio: SocketIO, config: dict[str, Any] | None = None):
        """
        Initialize streaming buffer.

        Args:
            socketio: Flask-SocketIO instance for broadcasting
            config: Configuration dictionary with buffer settings
        """
        self.socketio = socketio
        self.config = config or {}

        # Buffer configuration
        self.buffer_interval_ms = self.config.get('STREAMING_BUFFER_INTERVAL', 250)  # 250ms default
        self.max_buffer_size = self.config.get('STREAMING_MAX_BUFFER_SIZE', 100)
        self.enabled = self.config.get('STREAMING_BUFFER_ENABLED', True)

        # Event buffers by type
        self.pattern_buffer: deque = deque(maxlen=self.max_buffer_size)
        self.indicator_buffer: deque = deque(maxlen=self.max_buffer_size)

        # Symbol-based aggregation for deduplication
        self.pattern_aggregator: dict[str, dict[str, Any]] = defaultdict(dict)
        self.indicator_aggregator: dict[str, dict[str, Any]] = defaultdict(dict)

        # Thread management
        self.flush_thread = None
        self.is_running = False
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            'events_buffered': 0,
            'events_flushed': 0,
            'events_deduplicated': 0,
            'flush_cycles': 0,
            'start_time': time.time()
        }

    def start(self):
        """Start the buffer flush thread."""
        if self.is_running:
            logger.warning("STREAMING-BUFFER: Already running")
            return

        if not self.enabled:
            logger.info("STREAMING-BUFFER: Buffering disabled, events will be sent immediately")
            return

        self.is_running = True
        self.flush_thread = threading.Thread(
            target=self._flush_loop,
            name="StreamingBufferFlush",
            daemon=True
        )
        self.flush_thread.start()
        logger.info(f"STREAMING-BUFFER: Started with {self.buffer_interval_ms}ms interval")

    def stop(self):
        """Stop the buffer flush thread and flush remaining events."""
        if not self.is_running:
            return

        logger.info("STREAMING-BUFFER: Stopping...")
        self.is_running = False

        # Final flush
        self._flush_all()

        if self.flush_thread and self.flush_thread.is_alive():
            self.flush_thread.join(timeout=2)

        logger.info(f"STREAMING-BUFFER: Stopped. Stats: {self.get_stats()}")

    def add_pattern(self, event_data: dict[str, Any]):
        """
        Add pattern detection event to buffer.

        Args:
            event_data: Pattern event data from Redis subscriber
        """
        if not self.enabled:
            # Direct send without buffering
            logger.debug(f"STREAMING-BUFFER: Direct send (buffering disabled) - pattern event")
            self.socketio.emit('streaming_pattern', event_data, namespace='/')
            return

        with self.lock:
            detection = event_data.get('detection', {})
            symbol = detection.get('symbol')
            # TickStockPL uses 'pattern' field, but we receive 'pattern_type' from RedisEventSubscriber
            pattern_type = detection.get('pattern_type') or detection.get('pattern') or detection.get('pattern_name')

            logger.debug(f"STREAMING-BUFFER: add_pattern called - symbol={symbol}, pattern={pattern_type}")

            if symbol and pattern_type:
                # Aggregate by symbol-pattern key
                key = f"{symbol}:{pattern_type}"

                # Always update aggregator with latest value
                self.pattern_aggregator[key] = event_data

                # Add to buffer if not already present
                if key not in [e.data.get('key') for e in self.pattern_buffer]:
                    event_data['key'] = key  # Add key for tracking
                    self.pattern_buffer.append(BufferedEvent(
                        event_type='streaming_pattern',
                        data=event_data,
                        priority=1 if detection.get('confidence', 0) >= 0.8 else 0
                    ))
                    self.stats['events_buffered'] += 1
            else:
                logger.warning(f"STREAMING-BUFFER: Pattern missing required fields - symbol={symbol}, pattern_type={pattern_type}")

    def add_indicator(self, event_data: dict[str, Any]):
        """
        Add indicator calculation event to buffer.

        Args:
            event_data: Indicator event data from Redis subscriber
        """
        if not self.enabled:
            # Direct send without buffering
            self.socketio.emit('streaming_indicator', event_data, namespace='/')
            return

        with self.lock:
            calculation = event_data.get('calculation', {})
            symbol = calculation.get('symbol')
            # TickStockPL uses 'indicator' field, not 'indicator_type'
            indicator_type = calculation.get('indicator_type') or calculation.get('indicator')

            if symbol and indicator_type:
                # Aggregate by symbol-indicator key
                key = f"{symbol}:{indicator_type}"

                logger.debug(f"STREAMING-BUFFER: add_indicator called - symbol={symbol}, indicator={indicator_type}")

                # Always update with latest value (indicators change frequently)
                self.indicator_aggregator[key] = event_data

                # Add to buffer if not already present
                if key not in [e.data.get('key') for e in self.indicator_buffer]:
                    event_data['key'] = key  # Add key for tracking
                    self.indicator_buffer.append(BufferedEvent(
                        event_type='streaming_indicator',
                        data=event_data,
                        priority=0
                    ))
                    self.stats['events_buffered'] += 1
            else:
                logger.warning(f"STREAMING-BUFFER: Indicator missing required fields - symbol={symbol}, indicator_type={indicator_type}")

    def _flush_loop(self):
        """Main loop for periodic buffer flushing."""
        logger.info(f"STREAMING-BUFFER: Flush loop started - interval={self.buffer_interval_ms}ms")

        while self.is_running:
            try:
                time.sleep(self.buffer_interval_ms / 1000.0)

                # Log flush attempt
                buffer_status = f"patterns={len(self.pattern_buffer)}, indicators={len(self.indicator_buffer)}"
                #logger.info(f"STREAMING-BUFFER: Flush cycle #{self.stats['flush_cycles']} - {buffer_status}")

                self._flush_all()
                self.stats['flush_cycles'] += 1

            except Exception as e:
                logger.error(f"STREAMING-BUFFER: Error in flush loop: {e}")

        logger.info("STREAMING-BUFFER: Flush loop ended")

    def _flush_all(self):
        """Flush all buffered events to WebSocket."""
        with self.lock:
            # Flush patterns
            if self.pattern_buffer:
                patterns_to_send = []

                # Get latest values from aggregator (like indicators do)
                for key, event_data in self.pattern_aggregator.items():
                    patterns_to_send.append(event_data)

                if patterns_to_send:
                    # Send batch
                    logger.info(f"STREAMING-BUFFER: Emitting batch of {len(patterns_to_send)} patterns to WebSocket")
                    self.socketio.emit('streaming_patterns_batch', {
                        'patterns': patterns_to_send[:20],  # Limit batch size
                        'count': len(patterns_to_send),
                        'timestamp': time.time()
                    }, namespace='/')

                    self.stats['events_flushed'] += len(patterns_to_send)
                    logger.info(f"STREAMING-BUFFER: Flushed {len(patterns_to_send)} patterns - Total flushed: {self.stats['events_flushed']}")

                self.pattern_buffer.clear()
                self.pattern_aggregator.clear()

            # Flush indicators
            if self.indicator_buffer:
                indicators_to_send = []

                # Get latest values from aggregator
                for key, event_data in self.indicator_aggregator.items():
                    indicators_to_send.append(event_data)

                if indicators_to_send:
                    # Send batch
                    logger.info(f"STREAMING-BUFFER: Emitting batch of {len(indicators_to_send)} indicators to WebSocket")
                    self.socketio.emit('streaming_indicators_batch', {
                        'indicators': indicators_to_send[:20],  # Limit batch size
                        'count': len(indicators_to_send),
                        'timestamp': time.time()
                    }, namespace='/')

                    self.stats['events_flushed'] += len(indicators_to_send)
                    logger.info(f"STREAMING-BUFFER: Flushed {len(indicators_to_send)} indicators - Total flushed: {self.stats['events_flushed']}")

                self.indicator_buffer.clear()
                self.indicator_aggregator.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get buffer statistics."""
        runtime = time.time() - self.stats['start_time']

        return {
            **self.stats,
            'runtime_seconds': round(runtime, 1),
            'buffer_efficiency': round(
                self.stats['events_deduplicated'] / max(self.stats['events_buffered'], 1) * 100, 1
            ),
            'flush_rate': round(self.stats['flush_cycles'] / max(runtime, 1), 1),
            'current_pattern_buffer': len(self.pattern_buffer),
            'current_indicator_buffer': len(self.indicator_buffer),
            'enabled': self.enabled,
            'buffer_interval_ms': self.buffer_interval_ms
        }

    def set_buffer_interval(self, interval_ms: int):
        """
        Dynamically adjust buffer interval.

        Args:
            interval_ms: New buffer interval in milliseconds
        """
        self.buffer_interval_ms = max(50, min(1000, interval_ms))  # Clamp between 50ms and 1s
        logger.info(f"STREAMING-BUFFER: Buffer interval set to {self.buffer_interval_ms}ms")

    def enable_buffering(self, enabled: bool):
        """
        Enable or disable buffering dynamically.

        Args:
            enabled: True to enable buffering, False for immediate send
        """
        self.enabled = enabled
        logger.info(f"STREAMING-BUFFER: Buffering {'enabled' if enabled else 'disabled'}")

        if enabled and not self.is_running:
            self.start()
        elif not enabled and self.is_running:
            self.stop()
