"""
Redis Subscriber for Daily Processing Events
Sprint 33 - Phase 1 Integration
Subscribes to TickStockPL processing channels and forwards events to the admin dashboard
"""

import json
import logging
import threading
from typing import Any

import redis
import requests

from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)

class ProcessingEventSubscriber:
    """Subscribes to TickStockPL processing events and forwards them to the admin dashboard"""

    def __init__(self, app_url: str = "http://localhost:5000"):
        """
        Initialize the processing event subscriber

        Args:
            app_url: Base URL of the Flask application
        """
        self.app_url = app_url
        self.redis_client = None
        self.pubsub = None
        self.thread = None
        self.running = False

        # Channels to subscribe to
        self.channels = [
            'tickstock:processing:status',
            'tickstock:processing:schedule',
            'tickstock:monitoring',  # For job progress updates
            'tickstock:errors',  # For processing errors
            'tickstock:data:import:status',  # Phase 2 import status
            # Sprint 36 - Cache sync channels
            'tickstock:cache:sync_triggered',
            'tickstock:cache:sync_complete',
            'tickstock:universe:updated',
            'tickstock:cache:ipo_assignment',
            'tickstock:cache:delisting_cleanup',
            # Sprint 33 Phase 3 - Indicator processing channels
            'tickstock:indicators:started',
            'tickstock:indicators:progress',
            'tickstock:indicators:completed',
            'tickstock:indicators:calculated',
        ]

        self._connect()

    def _connect(self):
        """Connect to Redis and setup pubsub"""
        config = get_config()
        self.redis_client = redis.Redis(
            host=config.get('REDIS_HOST', 'localhost'),
            port=config.get('REDIS_PORT', 6379),
            db=config.get('REDIS_DB', 0),
            decode_responses=True
        )

        # Test connection
        self.redis_client.ping()
        logger.info("Connected to Redis for processing events")

        # Setup pubsub
        self.pubsub = self.redis_client.pubsub()

    def start(self):
        """Start the subscriber thread"""
        if self.running:
            logger.warning("Subscriber is already running")
            return

        self.running = True

        # Subscribe to channels
        for channel in self.channels:
            self.pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")

        # Start listener thread
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        logger.info("Processing event subscriber started")

    def stop(self):
        """Stop the subscriber thread"""
        if not self.running:
            return

        self.running = False

        # Unsubscribe from all channels
        if self.pubsub:
            self.pubsub.unsubscribe()

        # Wait for thread to finish
        if self.thread:
            self.thread.join(timeout=5)

        # Close connections
        if self.pubsub:
            self.pubsub.close()
        if self.redis_client:
            self.redis_client.close()

        logger.info("Processing event subscriber stopped")

    def _listen(self):
        """Listen for events on subscribed channels"""
        while self.running:
            try:
                # Get message with timeout
                message = self.pubsub.get_message(timeout=1.0)

                if message and message['type'] == 'message':
                    self._handle_message(message)

            except redis.ConnectionError as e:
                logger.error(f"Redis connection error: {e}")
                self._handle_connection_error()

            except Exception as e:
                logger.error(f"Error in subscriber loop: {e}")

    def _handle_message(self, message: dict[str, Any]):
        """Handle incoming Redis message"""
        try:
            channel = message['channel']
            data = message['data']

            # Parse JSON data
            try:
                event_data = json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse message from {channel}: {data}")
                return

            # Route based on channel
            if channel == 'tickstock:processing:status':
                self._handle_processing_status(event_data)

            elif channel == 'tickstock:processing:schedule':
                self._handle_schedule_update(event_data)

            elif channel == 'tickstock:monitoring':
                self._handle_monitoring_event(event_data)

            elif channel == 'tickstock:errors':
                self._handle_error_event(event_data)

            elif channel == 'tickstock:data:import:status':
                self._handle_import_status(event_data)

            # Sprint 36 - Cache sync events
            elif channel == 'tickstock:cache:sync_triggered':
                self._handle_cache_sync_triggered(event_data)

            elif channel == 'tickstock:cache:sync_complete':
                self._handle_cache_sync_complete(event_data)

            elif channel == 'tickstock:universe:updated':
                self._handle_universe_updated(event_data)

            elif channel == 'tickstock:cache:ipo_assignment':
                self._handle_ipo_assignment(event_data)

            elif channel == 'tickstock:cache:delisting_cleanup':
                self._handle_delisting_cleanup(event_data)

            # Sprint 33 Phase 3 - Indicator processing events
            elif channel == 'tickstock:indicators:started':
                self._handle_indicator_processing_started(event_data)

            elif channel == 'tickstock:indicators:progress':
                self._handle_indicator_progress_update(event_data)

            elif channel == 'tickstock:indicators:completed':
                self._handle_indicator_processing_completed(event_data)

            elif channel == 'tickstock:indicators:calculated':
                self._handle_indicator_calculated(event_data)

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def _handle_processing_status(self, event: dict[str, Any]):
        """Handle processing status events"""
        event_type = event.get('event')

        if event_type in ['daily_processing_started', 'daily_processing_progress', 'daily_processing_completed']:
            self._forward_event_to_app(event)
            logger.info(f"Processing event: {event_type}")

    def _handle_schedule_update(self, event: dict[str, Any]):
        """Handle schedule update events"""
        if event.get('event') == 'schedule_updated':
            self._forward_event_to_app(event)
            logger.info("Schedule updated")

    def _handle_monitoring_event(self, event: dict[str, Any]):
        """Handle monitoring events that relate to processing"""
        event_type = event.get('event')

        # Forward job progress updates
        if event_type == 'job_progress_update':
            payload = event.get('payload', {})
            if payload.get('phase') in ['data_import', 'indicator_processing', 'pattern_detection']:
                self._forward_event_to_app(event)
                logger.debug(f"Job progress: {payload.get('phase')} - {payload.get('percentage')}%")

    def _handle_error_event(self, event: dict[str, Any]):
        """Handle error events related to processing"""
        payload = event.get('payload', {})
        component = payload.get('component', '')

        # Forward processing-related errors
        if 'processing' in component or 'import' in component or 'scheduler' in component:
            logger.error(f"Processing error: {payload.get('message')}")
            # Could forward to app for display in UI

    def _handle_import_status(self, event: dict[str, Any]):
        """Handle Phase 2 data import status events"""
        event_type = event.get('event')

        if event_type in ['data_import_started', 'data_import_completed', 'symbol_processing_complete']:
            self._forward_event_to_app(event)
            logger.info(f"Import event: {event_type}")

    def _handle_cache_sync_triggered(self, event: dict[str, Any]):
        """Handle cache sync triggered event"""
        payload = event.get('payload', {})
        job_id = payload.get('job_id')
        mode = payload.get('mode', 'unknown')

        logger.info(f"Cache sync triggered - Job ID: {job_id}, Mode: {mode}")

        # Store event for admin dashboard
        cache_event = {
            'event': 'cache_sync_triggered',
            'timestamp': event.get('timestamp'),
            'source': event.get('source'),
            'version': event.get('version'),
            'payload': payload
        }
        self._forward_event_to_app(cache_event)

    def _handle_cache_sync_complete(self, event: dict[str, Any]):
        """Handle cache sync completion event"""
        payload = event.get('payload', {})
        job_id = payload.get('job_id')
        status = payload.get('status')
        total_changes = payload.get('total_changes', 0)
        duration = payload.get('duration_seconds', 0)

        logger.info(f"Cache sync completed - Job ID: {job_id}, Status: {status}, Changes: {total_changes}")

        # Store event for admin dashboard
        cache_event = {
            'event': 'cache_sync_completed',
            'timestamp': event.get('timestamp'),
            'source': event.get('source'),
            'version': event.get('version'),
            'payload': payload
        }
        self._forward_event_to_app(cache_event)

    def _handle_universe_updated(self, event: dict[str, Any]):
        """Handle universe update events"""
        payload = event.get('payload', {})
        universe = payload.get('universe')
        action = payload.get('action')

        logger.debug(f"Universe updated: {universe} - Action: {action}")

        # Could trigger cache refresh in the app
        # For now, just log it

    def _handle_ipo_assignment(self, event: dict[str, Any]):
        """Handle IPO assignment events"""
        payload = event.get('payload', {})
        symbol = payload.get('symbol')
        universe = payload.get('universe')

        logger.info(f"IPO assigned: {symbol} -> {universe}")

        # Could notify admin dashboard about new IPOs

    def _handle_delisting_cleanup(self, event: dict[str, Any]):
        """Handle delisting cleanup events"""
        payload = event.get('payload', {})
        removed_count = payload.get('removed_count', 0)

        logger.info(f"Delisted stocks cleaned up: {removed_count} removed")

    def _handle_indicator_processing_started(self, event: dict[str, Any]):
        """Handle indicator processing started event"""
        payload = event.get('payload', {})
        run_id = payload.get('run_id')
        total_symbols = payload.get('total_symbols', 0)
        total_indicators = payload.get('total_indicators', 0)

        logger.info(f"Indicator processing started - Run ID: {run_id}, Symbols: {total_symbols}, Indicators: {total_indicators}")

        # Forward to admin dashboard
        indicator_event = {
            'event': 'indicator_processing_started',
            'timestamp': event.get('timestamp'),
            'source': event.get('source'),
            'version': event.get('version'),
            'payload': payload
        }
        self._forward_event_to_app(indicator_event)

    def _handle_indicator_progress_update(self, event: dict[str, Any]):
        """Handle indicator processing progress update"""
        payload = event.get('payload', {})
        run_id = payload.get('run_id')
        completed_symbols = payload.get('completed_symbols', 0)
        total_symbols = payload.get('total_symbols', 0)
        percent_complete = payload.get('percent_complete', 0)
        current_symbol = payload.get('current_symbol', '')
        eta_seconds = payload.get('eta_seconds', 0)

        logger.debug(f"Indicator progress - Run ID: {run_id}, Progress: {percent_complete:.1f}%, Current: {current_symbol}")

        # Forward to admin dashboard
        indicator_event = {
            'event': 'indicator_progress',
            'timestamp': event.get('timestamp'),
            'source': event.get('source'),
            'version': event.get('version'),
            'payload': payload
        }
        self._forward_event_to_app(indicator_event)

    def _handle_indicator_processing_completed(self, event: dict[str, Any]):
        """Handle indicator processing completed event"""
        payload = event.get('payload', {})
        run_id = payload.get('run_id')
        total_symbols = payload.get('total_symbols', 0)
        successful_symbols = payload.get('successful_symbols', 0)
        failed_symbols = payload.get('failed_symbols', 0)
        total_indicators = payload.get('total_indicators', 0)
        successful_indicators = payload.get('successful_indicators', 0)
        failed_indicators = payload.get('failed_indicators', 0)
        success_rate = payload.get('success_rate', 0)
        duration_seconds = payload.get('duration_seconds', 0)

        logger.info(f"Indicator processing completed - Run ID: {run_id}, Success Rate: {success_rate:.1f}%, Duration: {duration_seconds}s")

        # Forward to admin dashboard
        indicator_event = {
            'event': 'indicator_processing_completed',
            'timestamp': event.get('timestamp'),
            'source': event.get('source'),
            'version': event.get('version'),
            'payload': payload
        }
        self._forward_event_to_app(indicator_event)

    def _handle_indicator_calculated(self, event: dict[str, Any]):
        """Handle individual indicator calculated event (optional real-time updates)"""
        payload = event.get('payload', {})
        symbol = payload.get('symbol', '')
        indicator = payload.get('indicator', '')
        timeframe = payload.get('timeframe', '')
        values = payload.get('values', {})

        logger.debug(f"Indicator calculated - {symbol}: {indicator} ({timeframe})")

        # For now, just log individual calculations
        # In the future, could forward to real-time displays showing specific symbols
        # self._forward_event_to_app(indicator_event)

    def _forward_event_to_app(self, event: dict[str, Any]):
        """Forward event to Flask application"""
        try:
            # Post to internal endpoint
            url = f"{self.app_url}/api/admin/processing/store-event"
            response = requests.post(url, json=event, timeout=5)

            if response.status_code != 200:
                logger.warning(f"Failed to forward event: {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error forwarding event to app: {e}")

    def _handle_connection_error(self):
        """Handle Redis connection errors with reconnection logic"""
        if not self.running:
            return

        logger.info("Attempting to reconnect to Redis...")

        # Wait before reconnecting
        import time
        time.sleep(5)

        try:
            # Reconnect
            self._connect()

            # Resubscribe to channels
            for channel in self.channels:
                self.pubsub.subscribe(channel)

            logger.info("Successfully reconnected to Redis")

        except Exception as e:
            logger.error(f"Failed to reconnect: {e}")


def create_processing_subscriber(app):
    """
    Create and start a processing event subscriber for the Flask app

    Args:
        app: Flask application instance

    Returns:
        ProcessingEventSubscriber instance
    """
    # Get app URL from config or use default
    app_url = app.config.get('APP_URL', 'http://localhost:5000')

    subscriber = ProcessingEventSubscriber(app_url)
    subscriber.start()

    # Register cleanup on app shutdown
    @app.teardown_appcontext
    def shutdown_subscriber(exception=None):
        if subscriber:
            subscriber.stop()

    return subscriber


# Test script
if __name__ == "__main__":
    import time

    logging.basicConfig(level=logging.INFO)

    # Create test subscriber
    subscriber = ProcessingEventSubscriber()

    try:
        # Start subscriber
        subscriber.start()
        logger.info("Test subscriber started. Listening for events...")

        # Publish test events
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Test processing started event
        test_event = {
            'event': 'daily_processing_started',
            'timestamp': '2025-01-25T21:10:00Z',
            'source': 'test',
            'version': '1.0',
            'payload': {
                'run_id': 'test-001',
                'symbols_count': 100,
                'trigger_type': 'manual'
            }
        }
        r.publish('tickstock:processing:status', json.dumps(test_event))
        logger.info("Published test event: daily_processing_started")

        # Wait a bit
        time.sleep(2)

        # Test progress event
        progress_event = {
            'event': 'daily_processing_progress',
            'timestamp': '2025-01-25T21:11:00Z',
            'source': 'test',
            'version': '1.0',
            'payload': {
                'run_id': 'test-001',
                'phase': 'data_import',
                'symbols_completed': 50,
                'symbols_total': 100,
                'percent_complete': 50.0,
                'current_symbol': 'AAPL',
                'estimated_completion': '2025-01-25T21:20:00Z'
            }
        }
        r.publish('tickstock:processing:status', json.dumps(progress_event))
        logger.info("Published test event: daily_processing_progress")

        # Wait a bit more
        time.sleep(2)

        # Test completion event
        complete_event = {
            'event': 'daily_processing_completed',
            'timestamp': '2025-01-25T21:20:00Z',
            'source': 'test',
            'version': '1.0',
            'payload': {
                'run_id': 'test-001',
                'status': 'success',
                'duration_seconds': 600,
                'symbols_processed': 100,
                'symbols_failed': 0
            }
        }
        r.publish('tickstock:processing:status', json.dumps(complete_event))
        logger.info("Published test event: daily_processing_completed")

        # Keep running
        logger.info("Press Ctrl+C to stop")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopping test subscriber...")
        subscriber.stop()
        logger.info("Test complete")
