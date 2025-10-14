"""
Redis Event Subscriber Service
Consumes TickStockPL events and forwards them to Flask-SocketIO for real-time UI updates.

Sprint 10 Phase 2: Enhanced Redis Event Consumption
- Subscribe to TickStockPL event channels (patterns, backtest progress/results)
- Process and validate incoming messages
- Forward events to Flask-SocketIO for browser broadcasting
- Handle offline users with message persistence (Redis Streams)
"""

import json
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import redis
from flask_socketio import SocketIO

from src.core.services.integration_logger import (
    IntegrationPoint,
    flow_logger,
    log_websocket_delivery,
)

logger = logging.getLogger(__name__)

# Forward declaration to avoid circular import
BacktestJobManager = None

class EventType(Enum):
    """TickStockPL event types we consume."""
    PATTERN_DETECTED = "pattern_detected"
    BACKTEST_PROGRESS = "backtest_progress"
    BACKTEST_RESULT = "backtest_result"
    SYSTEM_HEALTH = "system_health"
    # Phase 5 Streaming events
    STREAMING_SESSION_STARTED = "streaming_session_started"
    STREAMING_SESSION_STOPPED = "streaming_session_stopped"
    STREAMING_HEALTH = "streaming_health"
    STREAMING_PATTERN = "streaming_pattern"
    STREAMING_INDICATOR = "streaming_indicator"
    INDICATOR_ALERT = "indicator_alert"
    CRITICAL_ALERT = "critical_alert"

@dataclass
class TickStockEvent:
    """Structured representation of a TickStockPL event."""
    event_type: EventType
    source: str
    timestamp: float
    data: dict[str, Any]
    channel: str

    def to_websocket_dict(self) -> dict[str, Any]:
        """Convert event to WebSocket-friendly format."""
        return {
            'event_type': self.event_type.value,
            'source': self.source,
            'timestamp': self.timestamp,
            'data': self.data,
            'channel': self.channel
        }

class RedisEventSubscriber:
    """
    Redis event subscriber for TickStockPL integration.
    
    Consumes events from TickStockPL services and forwards them to Flask-SocketIO
    for real-time UI updates. Handles connection resilience and message persistence.
    """

    def __init__(self, redis_client: redis.Redis, socketio: SocketIO, config: dict[str, Any],
                 backtest_manager=None, flask_app=None):
        """Initialize Redis event subscriber."""
        self.redis_client = redis_client
        self.socketio = socketio
        self.config = config
        self.backtest_manager = backtest_manager
        self.flask_app = flask_app

        # Subscription management
        self.pubsub = None
        self.subscriber_thread = None
        self.is_running = False

        # Event handlers
        self.event_handlers: dict[EventType, list[Callable]] = {
            EventType.PATTERN_DETECTED: [],
            EventType.BACKTEST_PROGRESS: [],
            EventType.BACKTEST_RESULT: [],
            EventType.SYSTEM_HEALTH: [],
            # Phase 5 handlers
            EventType.STREAMING_SESSION_STARTED: [],
            EventType.STREAMING_SESSION_STOPPED: [],
            EventType.STREAMING_HEALTH: [],
            EventType.STREAMING_PATTERN: [],
            EventType.STREAMING_INDICATOR: [],
            EventType.INDICATOR_ALERT: [],
            EventType.CRITICAL_ALERT: []
        }

        # TickStockPL event channels
        self.channels = {
            'tickstock.events.patterns': EventType.PATTERN_DETECTED,
            'tickstock.events.backtesting.progress': EventType.BACKTEST_PROGRESS,
            'tickstock.events.backtesting.results': EventType.BACKTEST_RESULT,
            'tickstock.health.status': EventType.SYSTEM_HEALTH,
            # Phase 5 streaming channels
            'tickstock:streaming:session_started': EventType.STREAMING_SESSION_STARTED,
            'tickstock:streaming:session_stopped': EventType.STREAMING_SESSION_STOPPED,
            'tickstock:streaming:health': EventType.STREAMING_HEALTH,
            'tickstock:patterns:streaming': EventType.STREAMING_PATTERN,
            'tickstock:patterns:detected': EventType.STREAMING_PATTERN,  # High confidence patterns
            'tickstock:indicators:streaming': EventType.STREAMING_INDICATOR,
            'tickstock:alerts:indicators': EventType.INDICATOR_ALERT,
            'tickstock:alerts:critical': EventType.CRITICAL_ALERT
        }

        # User subscription tracking
        self.user_subscriptions: dict[str, list[str]] = {}  # user_id -> [pattern_names]

        # Statistics
        self.stats = {
            'events_received': 0,
            'events_processed': 0,
            'events_forwarded': 0,
            'events_dropped': 0,
            'connection_errors': 0,
            'last_event_time': None,
            'start_time': time.time(),
            'last_heartbeat': None
        }

        # Heartbeat tracking
        self.heartbeat_interval = 60  # Log heartbeat every 60 seconds
        self.last_heartbeat_log = time.time()

        # Phase 5 Streaming state
        self.current_streaming_session = None
        self.latest_streaming_health = {
            'status': 'unknown',
            'active_symbols': 0,
            'ticks_per_second': 0.0,
            'data_flow': {
                'ticks_per_second': 0.0
            }
        }
        self.streaming_buffer = None  # Will be set if buffering is enabled

    def start(self) -> bool:
        """Start the Redis event subscription service."""
        if self.is_running:
            logger.warning("REDIS-SUBSCRIBER: Service already running")
            return True

        try:
            logger.info("REDIS-SUBSCRIBER: Starting service...")

            # Test Redis connection
            if not self._test_redis_connection():
                return False

            # Initialize pubsub
            self.pubsub = self.redis_client.pubsub()

            # Subscribe to TickStockPL channels
            channel_list = list(self.channels.keys())
            self.pubsub.subscribe(channel_list)

            logger.info(f"REDIS-SUBSCRIBER: Subscribed to {len(channel_list)} channels: {channel_list}")

            # Log to database that subscriptions are active
            # Start subscriber thread
            self.is_running = True
            self.subscriber_thread = threading.Thread(
                target=self._subscriber_loop,
                name="RedisEventSubscriber",
                daemon=True
            )
            self.subscriber_thread.start()

            logger.info("REDIS-SUBSCRIBER: Service started successfully")
            return True

        except Exception as e:
            logger.error(f"REDIS-SUBSCRIBER: Failed to start service: {e}")
            self.is_running = False
            return False

    def stop(self):
        """Stop the Redis event subscription service."""
        if not self.is_running:
            return

        logger.info("REDIS-SUBSCRIBER: Stopping service...")
        self.is_running = False

        try:
            if self.pubsub:
                self.pubsub.unsubscribe()
                self.pubsub.close()

            if self.subscriber_thread and self.subscriber_thread.is_alive():
                self.subscriber_thread.join(timeout=5)

        except Exception as e:
            logger.error(f"REDIS-SUBSCRIBER: Error during shutdown: {e}")

        logger.info("REDIS-SUBSCRIBER: Service stopped")

    def _test_redis_connection(self) -> bool:
        """Test Redis connection before starting subscription."""
        try:
            self.redis_client.ping()
            logger.info("REDIS-SUBSCRIBER: Redis connection verified")
            return True
        except Exception as e:
            logger.error(f"REDIS-SUBSCRIBER: Redis connection failed: {e}")
            return False

    def _subscriber_loop(self):
        """Main subscriber loop that processes incoming events."""
        logger.info("REDIS-SUBSCRIBER: Entering subscriber loop")

        while self.is_running:
            try:
                # Get message with timeout
                message = self.pubsub.get_message(timeout=1.0)

                # Check for heartbeat logging
                current_time = time.time()
                if current_time - self.last_heartbeat_log >= self.heartbeat_interval:
                    self._log_heartbeat()
                    self.last_heartbeat_log = current_time

                if message is None:
                    continue

                # Log subscription confirmation messages
                if message['type'] in ['subscribe', 'unsubscribe']:
                    channel_name = message.get('channel', b'unknown').decode('utf-8') if isinstance(message.get('channel'), bytes) else message.get('channel')
                    logger.info(f"REDIS-SUBSCRIBER: Channel {message['type']}: {channel_name}")

                    # Log subscription status to database
                    continue

                # Process actual messages
                if message['type'] == 'message':
                    self._process_message(message)

            except redis.ConnectionError as e:
                logger.error(f"REDIS-SUBSCRIBER: Connection error: {e}")
                self.stats['connection_errors'] += 1
                self._handle_connection_error()

            except Exception as e:
                logger.error(f"REDIS-SUBSCRIBER: Unexpected error in subscriber loop: {e}")
                time.sleep(1)  # Prevent tight error loop

        logger.info("REDIS-SUBSCRIBER: Exited subscriber loop")

    def _process_message(self, message: dict[str, Any]):
        """Process a Redis message and forward to WebSocket."""
        try:
            self.stats['events_received'] += 1

            # Start integration flow tracking
            flow_id = None

            channel = message['channel']
            data = message['data']

            # Decode message data
            if isinstance(data, bytes):
                data = data.decode('utf-8')

            # Parse JSON
            try:
                event_data = json.loads(data)
            except json.JSONDecodeError as e:
                logger.error(f"REDIS-SUBSCRIBER: Invalid JSON in message from {channel}: {e}")
                self.stats['events_dropped'] += 1
                return

            # Create structured event
            event_type = self.channels.get(channel)
            if not event_type:
                logger.warning(f"REDIS-SUBSCRIBER: Unknown channel: {channel}")
                self.stats['events_dropped'] += 1
                return

            event = TickStockEvent(
                event_type=event_type,
                source=event_data.get('source', 'unknown'),
                timestamp=event_data.get('timestamp', time.time()),
                data=event_data,
                channel=channel
            )

            # Add flow_id to event data for downstream logging
            if flow_id:
                event.data['_flow_id'] = flow_id

            # Process event
            self._handle_event(event)
            self.stats['events_processed'] += 1
            self.stats['last_event_time'] = time.time()

        except Exception as e:
            logger.error(f"REDIS-SUBSCRIBER: Error processing message: {e}")
            self.stats['events_dropped'] += 1

    def _handle_event(self, event: TickStockEvent):
        """Handle a processed TickStockPL event."""
        try:
            # Log event for debugging
            # Handled by integration logger

            # Apply user filtering for pattern events
            if event.event_type == EventType.PATTERN_DETECTED:
                self._handle_pattern_event(event)
            elif event.event_type == EventType.BACKTEST_PROGRESS:
                self._handle_backtest_progress(event)
            elif event.event_type == EventType.BACKTEST_RESULT:
                self._handle_backtest_result(event)
            elif event.event_type == EventType.SYSTEM_HEALTH:
                self._handle_system_health(event)
            # Phase 5 streaming events
            elif event.event_type == EventType.STREAMING_SESSION_STARTED:
                self._handle_streaming_session_started(event)
            elif event.event_type == EventType.STREAMING_SESSION_STOPPED:
                self._handle_streaming_session_stopped(event)
            elif event.event_type == EventType.STREAMING_HEALTH:
                self._handle_streaming_health(event)
            elif event.event_type == EventType.STREAMING_PATTERN:
                self._handle_streaming_pattern(event)
            elif event.event_type == EventType.STREAMING_INDICATOR:
                self._handle_streaming_indicator(event)
            elif event.event_type == EventType.INDICATOR_ALERT:
                self._handle_indicator_alert(event)
            elif event.event_type == EventType.CRITICAL_ALERT:
                self._handle_critical_alert(event)

            # Call registered event handlers
            for handler in self.event_handlers.get(event.event_type, []):
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"REDIS-SUBSCRIBER: Event handler error: {e}")

        except Exception as e:
            logger.error(f"REDIS-SUBSCRIBER: Error handling event: {e}")

    def _handle_pattern_event(self, event: TickStockEvent):
        """Handle pattern detection events with user filtering."""
        # Handle potential double-nested data structure from TickStockPL
        if 'data' in event.data and 'data' in event.data.get('data', {}):
            # Double-nested: event.data.data.data contains the actual pattern data
            pattern_data = event.data['data']['data']
            flow_id = event.data.get('_flow_id') or event.data['data'].get('flow_id')
        elif 'data' in event.data:
            # Single-nested: event.data.data contains the pattern data
            pattern_data = event.data['data']
            flow_id = event.data.get('_flow_id') or event.data.get('flow_id')
        else:
            # Direct: event.data contains the pattern data
            pattern_data = event.data
            flow_id = event.data.get('_flow_id') or event.data.get('flow_id')

        # Try to get pattern from 'pattern' field (new format)
        pattern_name = pattern_data.get('pattern')

        # Fallback to 'pattern_name' field (old format) if pattern is not found
        if not pattern_name:
            pattern_name = pattern_data.get('pattern_name')

        symbol = pattern_data.get('symbol')
        confidence = pattern_data.get('confidence', 0)

        # Database integration logging for EVENT_PARSED
        if pattern_name and symbol:
            # File-based integration logging using correct enum
            flow_logger.log_checkpoint('', IntegrationPoint.EVENT_PARSED,
                                     f"{pattern_name}@{symbol}")

        if not pattern_name or not symbol:
            logger.warning("REDIS-SUBSCRIBER: Pattern event missing required fields")
            return

        # Execute within Flask app context
        def emit_pattern_alert():
            try:
                # Get pattern alert manager from Flask app context
                pattern_alert_manager = getattr(self.flask_app, 'pattern_alert_manager', None)

                if pattern_alert_manager:
                    # Get users who should receive this alert
                    interested_users = pattern_alert_manager.get_users_for_alert(
                        pattern_name, symbol, confidence
                    )

                    if interested_users:
                        # Send targeted alerts to specific users
                        websocket_data = {
                            'type': 'pattern_alert',
                            'event': event.to_websocket_dict()
                        }

                        # Only emit if socketio is available
                        if self.socketio:
                            for user_id in interested_users:
                                # Emit to specific user rooms (if using Socket.IO rooms)
                                self.socketio.emit('pattern_alert', websocket_data, room=f'user_{user_id}')

                            self.stats['events_forwarded'] += len(interested_users)
                        else:
                            logger.warning(f"REDIS-SUBSCRIBER: SocketIO not available, cannot emit to {len(interested_users)} users")

                        # Database integration logging for WEBSOCKET_DELIVERED
                        # File-based integration logging
                        log_websocket_delivery(pattern_name, symbol, len(interested_users))
                    else:
                        logger.debug(f"REDIS-SUBSCRIBER: No users subscribed to {pattern_name} on {symbol}")
                else:
                    # Fallback: Broadcast to all users (backward compatibility)
                    websocket_data = {
                        'type': 'pattern_alert',
                        'event': event.to_websocket_dict()
                    }

                    # Only emit if socketio is available
                    if self.socketio:
                        # Use namespace parameter instead of broadcast for Flask-SocketIO
                        self.socketio.emit('pattern_alert', websocket_data, namespace='/')
                        self.stats['events_forwarded'] += 1
                        logger.debug(f"REDIS-SUBSCRIBER: Pattern alert broadcasted - {pattern_name} on {symbol}")
                    else:
                        logger.warning(f"REDIS-SUBSCRIBER: SocketIO not available, cannot broadcast pattern alert for {pattern_name}")

                    # Database integration logging for broadcast
            except Exception as e:
                logger.error(f"REDIS-SUBSCRIBER: Error in pattern filtering: {e}")
                # Fallback to broadcast on error
                try:
                    websocket_data = {
                        'type': 'pattern_alert',
                        'event': event.to_websocket_dict()
                    }

                    # Only emit if socketio is available
                    if self.socketio:
                        self.socketio.emit('pattern_alert', websocket_data, namespace='/')
                        self.stats['events_forwarded'] += 1
                    else:
                        logger.warning(f"REDIS-SUBSCRIBER: SocketIO not available, cannot emit pattern alert for {pattern_name}")

                    # Database integration logging for error fallback
                except Exception as emit_error:
                    logger.error(f"REDIS-SUBSCRIBER: Failed to emit pattern alert: {emit_error}")

        # Execute within Flask app context if available
        if self.flask_app:
            with self.flask_app.app_context():
                emit_pattern_alert()
        else:
            emit_pattern_alert()

    def _handle_backtest_progress(self, event: TickStockEvent):
        """Handle backtest progress updates."""
        progress_data = event.data
        job_id = progress_data.get('job_id')
        progress = progress_data.get('progress', 0)
        current_symbol = progress_data.get('current_symbol')
        estimated_completion = progress_data.get('estimated_completion')

        if not job_id:
            logger.warning("REDIS-SUBSCRIBER: Backtest progress missing job_id")
            return

        # Update job progress in BacktestJobManager
        if self.backtest_manager:
            self.backtest_manager.update_job_progress(
                job_id, progress, current_symbol, estimated_completion
            )

        # Broadcast backtest progress to all users
        websocket_data = {
            'type': 'backtest_progress',
            'event': event.to_websocket_dict()
        }

        self.socketio.emit('backtest_progress', websocket_data, namespace='/')
        self.stats['events_forwarded'] += 1

        logger.debug(f"REDIS-SUBSCRIBER: Backtest progress forwarded for job {job_id}: {progress:.1%}")

    def _handle_backtest_result(self, event: TickStockEvent):
        """Handle completed backtest results."""
        result_data = event.data
        job_id = result_data.get('job_id')
        status = result_data.get('status', 'completed')
        results = result_data.get('results', {})

        if not job_id:
            logger.warning("REDIS-SUBSCRIBER: Backtest result missing job_id")
            return

        # Update job status in BacktestJobManager
        if self.backtest_manager:
            from src.core.services.backtest_job_manager import JobStatus
            job_status = JobStatus.COMPLETED if status == 'completed' else JobStatus.FAILED
            self.backtest_manager.complete_job(job_id, results, job_status)

        # Broadcast backtest results
        websocket_data = {
            'type': 'backtest_result',
            'event': event.to_websocket_dict()
        }

        self.socketio.emit('backtest_result', websocket_data, namespace='/')
        self.stats['events_forwarded'] += 1

        logger.info(f"REDIS-SUBSCRIBER: Backtest result forwarded for job {job_id}: {status}")

    def _handle_system_health(self, event: TickStockEvent):
        """Handle TickStockPL system health updates."""
        websocket_data = {
            'type': 'system_health',
            'event': event.to_websocket_dict()
        }

        # Broadcast to all connected users
        self.socketio.emit('system_health', websocket_data, namespace='/')
        self.stats['events_forwarded'] += 1

        logger.debug("REDIS-SUBSCRIBER: System health update forwarded")

    # Phase 5 Streaming Event Handlers
    def _handle_streaming_session_started(self, event: TickStockEvent):
        """Handle streaming session start event."""
        # Event format: {'type': 'streaming_session_started', 'session': {...}, 'timestamp': ...}
        session_data = event.data.get('session', {})
        session_id = session_data.get('session_id')
        symbol_universe_key = session_data.get('universe', session_data.get('symbol_universe_key'))
        start_time = session_data.get('started_at', session_data.get('start_time'))
        symbol_count = session_data.get('symbol_count', 0)
        status = session_data.get('status', 'unknown')

        logger.info(f"REDIS-SUBSCRIBER: Streaming session started - ID: {session_id}, Universe: {symbol_universe_key}, Symbols: {symbol_count}, Status: {status}")

        # Store session info for tracking
        self.current_streaming_session = {
            'session_id': session_id,
            'start_time': start_time,
            'universe': symbol_universe_key,
            'symbol_count': symbol_count,
            'status': status
        }

        # Debug: Confirm session stored
        logger.info(f"REDIS-SUBSCRIBER: current_streaming_session set to: {self.current_streaming_session}")

        # Broadcast to UI
        websocket_data = {
            'type': 'streaming_session_started',
            'session': self.current_streaming_session
        }
        self.socketio.emit('streaming_session', websocket_data, namespace='/')
        self.stats['events_forwarded'] += 1

    def _handle_streaming_session_stopped(self, event: TickStockEvent):
        """Handle streaming session stop event."""
        # Event format: {'type': 'streaming_session_stopped', 'session': {...}, 'timestamp': ...}
        session_data = event.data.get('session', event.data)
        session_id = session_data.get('session_id')
        stopped_at = session_data.get('stopped_at')
        duration_seconds = session_data.get('duration_seconds', 0)
        total_patterns = session_data.get('total_patterns', 0)
        total_indicators = session_data.get('total_indicators', 0)
        final_status = session_data.get('final_status', 'unknown')

        logger.info(f"REDIS-SUBSCRIBER: Streaming session stopped - ID: {session_id}, Duration: {duration_seconds}s, Patterns: {total_patterns}, Indicators: {total_indicators}, Status: {final_status}")

        # Clear session info
        self.current_streaming_session = None

        # Broadcast to UI
        websocket_data = {
            'type': 'streaming_session_stopped',
            'session_id': session_id,
            'stopped_at': stopped_at,
            'duration_seconds': duration_seconds,
            'total_patterns': total_patterns,
            'total_indicators': total_indicators,
            'final_status': final_status
        }
        self.socketio.emit('streaming_session', websocket_data, namespace='/')
        self.stats['events_forwarded'] += 1

    def _handle_streaming_health(self, event: TickStockEvent):
        """Handle streaming health metrics."""
        # Event format: {'type': 'streaming_health', 'health': {...}, 'timestamp': ...}
        health_data = event.data.get('health', event.data)  # Extract nested 'health' object

        # Store latest health metrics
        tps = health_data.get('ticks_per_second', 0.0)

        self.latest_streaming_health = {
            'timestamp': event.data.get('timestamp', health_data.get('timestamp')),
            'session_id': health_data.get('session_id'),
            'status': health_data.get('status'),
            'active_symbols': health_data.get('active_symbols', 0),
            'ticks_per_second': tps,
            'patterns_detected': health_data.get('patterns_detected', 0),
            'indicators_calculated': health_data.get('indicators_calculated', 0),
            # Legacy fields (may not be present in new format)
            'connection': health_data.get('connection', {}),
            'data_flow': {
                'ticks_per_second': tps,  # Populate for dashboard compatibility
                **health_data.get('data_flow', {})
            },
            'resources': health_data.get('resources', {}),
            'stale_symbols': health_data.get('stale_symbols', {})
        }

        logger.info(f"REDIS-SUBSCRIBER: Streaming health update received - Status: {health_data.get('status')}, Active Symbols: {health_data.get('active_symbols', 0)}, TPS: {health_data.get('ticks_per_second', 0.0)}")

        # Check for critical issues
        if health_data.get('status') == 'critical':
            logger.error(f"REDIS-SUBSCRIBER: Streaming health critical - Issues: {health_data.get('issues')}")

        # Broadcast health update
        websocket_data = {
            'type': 'streaming_health',
            'health': self.latest_streaming_health
        }
        self.socketio.emit('streaming_health', websocket_data, namespace='/')
        self.stats['events_forwarded'] += 1

    def _handle_streaming_pattern(self, event: TickStockEvent):
        """Handle real-time streaming pattern detection."""
        detection = event.data.get('detection', event.data)

        pattern_type = detection.get('pattern_type')
        symbol = detection.get('symbol')
        confidence = detection.get('confidence', 0)
        timestamp = detection.get('timestamp')

        logger.debug(f"REDIS-SUBSCRIBER: Streaming pattern - {pattern_type} on {symbol} (confidence: {confidence})")

        # Broadcast pattern immediately (will be buffered by streaming handler)
        websocket_data = {
            'type': 'streaming_pattern',
            'detection': {
                'pattern_type': pattern_type,
                'symbol': symbol,
                'confidence': confidence,
                'timestamp': timestamp,
                'parameters': detection.get('parameters', {}),
                'timeframe': detection.get('timeframe', '1min')
            }
        }

        # Send to buffering handler if available
        if hasattr(self, 'streaming_buffer'):
            self.streaming_buffer.add_pattern(websocket_data)
        else:
            # Direct broadcast without buffering
            self.socketio.emit('streaming_pattern', websocket_data, namespace='/')

        self.stats['events_forwarded'] += 1

    def _handle_streaming_indicator(self, event: TickStockEvent):
        """Handle real-time streaming indicator calculation."""
        calculation = event.data.get('calculation', event.data)

        indicator_type = calculation.get('indicator_type')
        symbol = calculation.get('symbol')
        values = calculation.get('values', {})
        timestamp = calculation.get('timestamp')

        logger.debug(f"REDIS-SUBSCRIBER: Streaming indicator - {indicator_type} on {symbol}")

        # Broadcast indicator update
        websocket_data = {
            'type': 'streaming_indicator',
            'calculation': {
                'indicator_type': indicator_type,
                'symbol': symbol,
                'values': values,
                'timestamp': timestamp,
                'timeframe': calculation.get('timeframe', '1min')
            }
        }

        # Send to buffering handler if available
        if hasattr(self, 'streaming_buffer'):
            self.streaming_buffer.add_indicator(websocket_data)
        else:
            # Direct broadcast without buffering
            self.socketio.emit('streaming_indicator', websocket_data, namespace='/')

        self.stats['events_forwarded'] += 1

    def _handle_indicator_alert(self, event: TickStockEvent):
        """Handle indicator alert events (RSI, MACD, BB extremes)."""
        alert_data = event.data

        alert_type = alert_data.get('alert_type')
        symbol = alert_data.get('symbol')
        data = alert_data.get('data', {})
        timestamp = alert_data.get('timestamp')

        logger.info(f"REDIS-SUBSCRIBER: Indicator alert - {alert_type} on {symbol}")

        # Broadcast alert immediately (no buffering for alerts)
        websocket_data = {
            'type': 'indicator_alert',
            'alert': {
                'alert_type': alert_type,
                'symbol': symbol,
                'data': data,
                'timestamp': timestamp,
                'session_id': alert_data.get('session_id')
            }
        }

        self.socketio.emit('indicator_alert', websocket_data, namespace='/')
        self.stats['events_forwarded'] += 1

    def _handle_critical_alert(self, event: TickStockEvent):
        """Handle critical system alerts."""
        alert_data = event.data

        alert_type = alert_data.get('type')
        message = alert_data.get('message')
        severity = alert_data.get('severity', 'critical')

        logger.error(f"REDIS-SUBSCRIBER: Critical alert - {alert_type}: {message}")

        # Broadcast critical alert immediately
        websocket_data = {
            'type': 'critical_alert',
            'alert': {
                'type': alert_type,
                'message': message,
                'severity': severity,
                'timestamp': alert_data.get('timestamp'),
                'data': alert_data.get('data', {})
            }
        }

        self.socketio.emit('critical_alert', websocket_data, namespace='/')
        self.stats['events_forwarded'] += 1

    def _handle_connection_error(self):
        """Handle Redis connection errors with reconnection logic."""
        logger.warning("REDIS-SUBSCRIBER: Attempting to reconnect to Redis...")

        for attempt in range(3):
            try:
                time.sleep(2 ** attempt)  # Exponential backoff

                if self._test_redis_connection():
                    logger.info("REDIS-SUBSCRIBER: Reconnected to Redis successfully")
                    return

            except Exception as e:
                logger.error(f"REDIS-SUBSCRIBER: Reconnection attempt {attempt + 1} failed: {e}")

        logger.error("REDIS-SUBSCRIBER: Failed to reconnect after 3 attempts")

    def set_backtest_manager(self, backtest_manager):
        """Set the backtest manager after initialization."""
        self.backtest_manager = backtest_manager
        logger.info("REDIS-SUBSCRIBER: Backtest manager connection established")

    def add_event_handler(self, event_type: EventType, handler: Callable[[TickStockEvent], None]):
        """Add custom event handler for specific event types."""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        self.event_handlers[event_type].append(handler)
        logger.info(f"REDIS-SUBSCRIBER: Added handler for {event_type.value} events")

    def get_stats(self) -> dict[str, Any]:
        """Get subscriber statistics."""
        runtime = time.time() - self.stats['start_time']

        return {
            **self.stats,
            'runtime_seconds': round(runtime, 1),
            'events_per_second': round(self.stats['events_received'] / max(runtime, 1), 2),
            'is_running': self.is_running,
            'subscribed_channels': list(self.channels.keys()),
            'active_thread': self.subscriber_thread and self.subscriber_thread.is_alive()
        }

    def get_health_status(self) -> dict[str, Any]:
        """Get health status for monitoring."""
        stats = self.get_stats()

        # Check TickStockPL producer status
        tickstock_pl_online = self._check_tickstock_pl_status()

        # Determine health status
        if not self.is_running:
            status = 'error'
            message = 'Subscriber service not running'
        elif stats['connection_errors'] > 5:
            status = 'degraded'
            message = f"Multiple connection errors ({stats['connection_errors']})"
        elif not tickstock_pl_online:
            status = 'warning'
            message = 'TickStockPL producer appears offline - using fallback detection'
        elif stats['last_event_time'] and (time.time() - stats['last_event_time']) > 300:
            status = 'warning'
            message = 'No events received in last 5 minutes'
        else:
            status = 'healthy'
            message = 'Service operating normally'

        return {
            'status': status,
            'message': message,
            'stats': stats,
            'tickstock_pl_online': tickstock_pl_online,
            'last_check': time.time()
        }

    def _log_heartbeat(self):
        """Log periodic heartbeat to show system is alive and listening."""
        try:
            # Log heartbeat to database
            # Also log to standard logger
            logger.info(f"REDIS-SUBSCRIBER HEARTBEAT: Alive and listening on {len(self.channels)} channels | "
                       f"Events: {self.stats['events_received']} received, {self.stats['events_processed']} processed | "
                       f"Uptime: {round(time.time() - self.stats['start_time'])}s")

            self.stats['last_heartbeat'] = time.time()

        except Exception as e:
            logger.error(f"REDIS-SUBSCRIBER: Error logging heartbeat: {e}")

    def _check_tickstock_pl_status(self) -> bool:
        """Check if TickStockPL producer system is online."""
        try:
            # Check for TickStockPL heartbeat
            heartbeat = self.redis_client.get('tickstock:producer:heartbeat')
            if heartbeat:
                heartbeat_time = float(heartbeat)
                return (time.time() - heartbeat_time) < 60  # Within last minute

            # Check for recent pattern activity
            pattern_keys = self.redis_client.keys('tickstock:patterns:*')
            if pattern_keys:
                # Check if any pattern data is recent
                for key in pattern_keys[:5]:  # Check first 5 keys
                    ttl = self.redis_client.ttl(key)
                    if ttl > 0 and ttl < 3600:  # Fresh data (less than 1 hour old)
                        return True

            return False

        except Exception as e:
            logger.error(f"REDIS-SUBSCRIBER: Error checking TickStockPL status: {e}")
            return False
