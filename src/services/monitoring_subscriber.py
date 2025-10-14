"""
Redis Monitoring Event Subscriber
Subscribes to TickStockPL monitoring events and forwards to dashboard
Sprint 31 Implementation
"""

import json
import logging
import threading
from typing import Any

import redis
import requests

from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)


class MonitoringSubscriber:
    """Subscribes to TickStockPL monitoring events via Redis pub/sub"""

    def __init__(self, app_url: str = 'http://localhost:5000'):
        """
        Initialize the monitoring subscriber.

        Args:
            app_url: Base URL of the Flask application
        """
        self.app_url = app_url
        self.redis_client = None
        self.pubsub = None
        self.subscriber_thread = None
        self.running = False
        self.channel = 'tickstock:monitoring'

        # Redis connection parameters
        config = get_config()
        self.redis_config = {
            'host': config.get('REDIS_HOST', 'localhost'),
            'port': config.get('REDIS_PORT', 6379),
            'db': config.get('REDIS_DB', 0),
            'decode_responses': True
        }

    def connect(self) -> bool:
        """Establish Redis connection and subscribe to monitoring channel."""
        try:
            self.redis_client = redis.Redis(**self.redis_config)
            self.redis_client.ping()

            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(self.channel)

            logger.info(f"Successfully subscribed to Redis channel: {self.channel}")
            return True

        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            return False

    def start(self):
        """Start the subscriber in a background thread."""
        if not self.redis_client:
            if not self.connect():
                logger.error("Cannot start subscriber - Redis connection failed")
                return

        self.running = True
        self.subscriber_thread = threading.Thread(target=self._listen_for_events, daemon=True)
        self.subscriber_thread.start()
        logger.info("Monitoring subscriber started")

    def stop(self):
        """Stop the subscriber and clean up resources."""
        self.running = False

        if self.pubsub:
            try:
                self.pubsub.unsubscribe(self.channel)
                self.pubsub.close()
            except:
                pass

        if self.redis_client:
            try:
                self.redis_client.close()
            except:
                pass

        if self.subscriber_thread and self.subscriber_thread.is_alive():
            self.subscriber_thread.join(timeout=5)

        logger.info("Monitoring subscriber stopped")

    def _listen_for_events(self):
        """Main event listening loop."""
        logger.info(f"Starting to listen for events on {self.channel}")

        # Wait a moment for Flask routes to be fully initialized
        import time
        time.sleep(2)

        while self.running:
            try:
                # Get message with timeout to allow checking running flag
                message = self.pubsub.get_message(timeout=1.0)

                if message and message['type'] == 'message':
                    self._handle_message(message['data'])

            except redis.ConnectionError as e:
                logger.error(f"Lost Redis connection: {e}")
                self._handle_disconnection()

            except Exception as e:
                logger.error(f"Error processing message: {e}")

    def _handle_message(self, data: str):
        """
        Handle a received monitoring event.

        Args:
            data: JSON string containing the event data
        """
        try:
            event = json.loads(data)
            event_type = event.get('event_type')

            logger.debug(f"Received event: {event_type}")

            # Forward event to Flask app for storage and processing
            self._forward_to_app(event)

            # Handle specific event types
            if event_type == 'METRIC_UPDATE':
                self._handle_metric_update(event)
            elif event_type == 'ALERT_TRIGGERED':
                self._handle_alert_triggered(event)
            elif event_type == 'ALERT_RESOLVED':
                self._handle_alert_resolved(event)
            elif event_type == 'HEALTH_CHECK':
                self._handle_health_check(event)
            elif event_type == 'SYSTEM_STATUS':
                self._handle_system_status(event)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event data: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def _forward_to_app(self, event: dict[str, Any]):
        """
        Forward event to Flask app for storage.

        Args:
            event: Event dictionary to forward
        """
        try:
            response = requests.post(
                f"{self.app_url}/api/admin/monitoring/store-event",
                json=event,
                timeout=5
            )

            if not response.ok:
                logger.warning(f"Failed to forward event to app: {response.status_code}")

        except requests.RequestException as e:
            logger.error(f"Error forwarding event to app: {e}")

    def _handle_metric_update(self, event: dict[str, Any]):
        """Handle metric update events."""
        metrics = event.get('metrics', {})
        health_score = event.get('health_score', {})

        # Log critical metrics
        if metrics.get('system', {}).get('cpu_percent', 0) > 90:
            logger.warning(f"HIGH CPU: {metrics['system']['cpu_percent']}%")

        if metrics.get('system', {}).get('memory_percent', 0) > 85:
            logger.warning(f"HIGH MEMORY: {metrics['system']['memory_percent']}%")

        if health_score.get('overall', 100) < 70:
            logger.warning(f"LOW HEALTH SCORE: {health_score['overall']}")

    def _handle_alert_triggered(self, event: dict[str, Any]):
        """Handle alert triggered events."""
        alert = event.get('alert', {})
        level = alert.get('level', 'INFO')
        message = alert.get('message', 'Unknown alert')

        logger.warning(f"ALERT [{level}]: {message}")

        # For critical alerts, could trigger additional actions
        if level in ['CRITICAL', 'EMERGENCY']:
            logger.critical(f"CRITICAL ALERT: {message}")
            # Could send email, SMS, or other notifications here

    def _handle_alert_resolved(self, event: dict[str, Any]):
        """Handle alert resolved events."""
        alert_id = event.get('alert_id')
        logger.info(f"Alert resolved: {alert_id}")

    def _handle_health_check(self, event: dict[str, Any]):
        """Handle health check events."""
        health = event.get('health', {})
        overall_score = health.get('overall_score', 0)
        status = health.get('status', 'UNKNOWN')

        logger.info(f"Health Check: {status} (Score: {overall_score})")

        # Log component issues
        components = health.get('components', {})
        for name, component in components.items():
            if component.get('status') != 'OK':
                logger.warning(f"Component {name}: {component.get('status')} - {component.get('details')}")

    def _handle_system_status(self, event: dict[str, Any]):
        """Handle system status events."""
        status = event.get('status')
        details = event.get('details', {})

        logger.info(f"System Status: {status}")

        if status != 'RUNNING':
            logger.warning(f"System not running normally: {status}")

    def _handle_disconnection(self):
        """Handle Redis disconnection."""
        logger.warning("Attempting to reconnect to Redis...")

        # Wait before reconnecting
        import time
        time.sleep(5)

        # Try to reconnect
        if self.connect():
            logger.info("Successfully reconnected to Redis")
        else:
            logger.error("Failed to reconnect to Redis")
            # Could implement exponential backoff here

    def get_status(self) -> dict[str, Any]:
        """
        Get the current status of the subscriber.

        Returns:
            Dictionary containing subscriber status
        """
        return {
            'running': self.running,
            'connected': self.redis_client is not None and self.pubsub is not None,
            'channel': self.channel,
            'thread_alive': self.subscriber_thread.is_alive() if self.subscriber_thread else False
        }


# Global subscriber instance
_subscriber = None


def start_monitoring_subscriber(app_url: str = 'http://localhost:5000'):
    """
    Start the global monitoring subscriber.

    Args:
        app_url: Base URL of the Flask application
    """
    global _subscriber

    if _subscriber is None:
        _subscriber = MonitoringSubscriber(app_url)
        _subscriber.start()
        logger.info("Global monitoring subscriber started")
    else:
        logger.info("Monitoring subscriber already running")


def stop_monitoring_subscriber():
    """Stop the global monitoring subscriber."""
    global _subscriber

    if _subscriber is not None:
        _subscriber.stop()
        _subscriber = None
        logger.info("Global monitoring subscriber stopped")


def get_subscriber_status() -> dict[str, Any]:
    """
    Get the status of the global monitoring subscriber.

    Returns:
        Dictionary containing subscriber status
    """
    if _subscriber is not None:
        return _subscriber.get_status()
    return {
        'running': False,
        'connected': False,
        'channel': None,
        'thread_alive': False
    }


# Example usage for testing
if __name__ == "__main__":
    import time

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Start subscriber
    subscriber = MonitoringSubscriber()

    if subscriber.connect():
        print("Starting monitoring subscriber...")
        subscriber.start()

        try:
            # Run for a while
            print("Listening for events (press Ctrl+C to stop)...")
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping subscriber...")
            subscriber.stop()
            print("Subscriber stopped")
    else:
        print("Failed to connect to Redis")
