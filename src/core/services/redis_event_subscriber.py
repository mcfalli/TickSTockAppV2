"""
Redis Event Subscriber Service
Consumes TickStockPL events and forwards them to Flask-SocketIO for real-time UI updates.

Sprint 10 Phase 2: Enhanced Redis Event Consumption
- Subscribe to TickStockPL event channels (patterns, backtest progress/results)
- Process and validate incoming messages
- Forward events to Flask-SocketIO for browser broadcasting
- Handle offline users with message persistence (Redis Streams)
"""

import logging
import json
import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import redis
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

# Forward declaration to avoid circular import
BacktestJobManager = None

class EventType(Enum):
    """TickStockPL event types we consume."""
    PATTERN_DETECTED = "pattern_detected"
    BACKTEST_PROGRESS = "backtest_progress"
    BACKTEST_RESULT = "backtest_result"
    SYSTEM_HEALTH = "system_health"

@dataclass
class TickStockEvent:
    """Structured representation of a TickStockPL event."""
    event_type: EventType
    source: str
    timestamp: float
    data: Dict[str, Any]
    channel: str
    
    def to_websocket_dict(self) -> Dict[str, Any]:
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
    
    def __init__(self, redis_client: redis.Redis, socketio: SocketIO, config: Dict[str, Any], 
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
        self.event_handlers: Dict[EventType, List[Callable]] = {
            EventType.PATTERN_DETECTED: [],
            EventType.BACKTEST_PROGRESS: [],
            EventType.BACKTEST_RESULT: [],
            EventType.SYSTEM_HEALTH: []
        }
        
        # TickStockPL event channels
        self.channels = {
            'tickstock.events.patterns': EventType.PATTERN_DETECTED,
            'tickstock.events.backtesting.progress': EventType.BACKTEST_PROGRESS,
            'tickstock.events.backtesting.results': EventType.BACKTEST_RESULT,
            'tickstock.health.status': EventType.SYSTEM_HEALTH
        }
        
        # User subscription tracking
        self.user_subscriptions: Dict[str, List[str]] = {}  # user_id -> [pattern_names]
        
        # Statistics
        self.stats = {
            'events_received': 0,
            'events_processed': 0,
            'events_forwarded': 0,
            'events_dropped': 0,
            'connection_errors': 0,
            'last_event_time': None,
            'start_time': time.time()
        }
        
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
                
                if message is None:
                    continue
                    
                # Skip subscription confirmation messages
                if message['type'] in ['subscribe', 'unsubscribe']:
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
    
    def _process_message(self, message: Dict[str, Any]):
        """Process a Redis message and forward to WebSocket."""
        try:
            self.stats['events_received'] += 1
            
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
            logger.debug(f"REDIS-SUBSCRIBER: Handling {event.event_type.value} event from {event.source}")
            
            # Apply user filtering for pattern events
            if event.event_type == EventType.PATTERN_DETECTED:
                self._handle_pattern_event(event)
            elif event.event_type == EventType.BACKTEST_PROGRESS:
                self._handle_backtest_progress(event)
            elif event.event_type == EventType.BACKTEST_RESULT:
                self._handle_backtest_result(event)
            elif event.event_type == EventType.SYSTEM_HEALTH:
                self._handle_system_health(event)
            
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
        pattern_data = event.data
        pattern_name = pattern_data.get('pattern')
        symbol = pattern_data.get('symbol')
        confidence = pattern_data.get('confidence', 0)
        
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
                        
                        for user_id in interested_users:
                            # Emit to specific user rooms (if using Socket.IO rooms)
                            self.socketio.emit('pattern_alert', websocket_data, room=f'user_{user_id}')
                        
                        self.stats['events_forwarded'] += len(interested_users)
                        logger.info(f"REDIS-SUBSCRIBER: Pattern alert sent to {len(interested_users)} users - {pattern_name} on {symbol}")
                    else:
                        logger.debug(f"REDIS-SUBSCRIBER: No users subscribed to {pattern_name} on {symbol}")
                else:
                    # Fallback: Broadcast to all users (backward compatibility)
                    websocket_data = {
                        'type': 'pattern_alert',
                        'event': event.to_websocket_dict()
                    }
                    
                    # Use namespace parameter instead of broadcast for Flask-SocketIO
                    self.socketio.emit('pattern_alert', websocket_data, namespace='/')
                    self.stats['events_forwarded'] += 1
                    logger.info(f"REDIS-SUBSCRIBER: Pattern alert broadcasted (no filter) - {pattern_name} on {symbol}")
                    
            except Exception as e:
                logger.error(f"REDIS-SUBSCRIBER: Error in pattern filtering: {e}")
                # Fallback to broadcast on error
                try:
                    websocket_data = {
                        'type': 'pattern_alert',
                        'event': event.to_websocket_dict()
                    }
                    
                    self.socketio.emit('pattern_alert', websocket_data, namespace='/')
                    self.stats['events_forwarded'] += 1
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
    
    def get_stats(self) -> Dict[str, Any]:
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
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring."""
        stats = self.get_stats()
        
        # Determine health status
        if not self.is_running:
            status = 'error'
            message = 'Subscriber service not running'
        elif stats['connection_errors'] > 5:
            status = 'degraded'
            message = f"Multiple connection errors ({stats['connection_errors']})"
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
            'last_check': time.time()
        }