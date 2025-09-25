"""Sprint 32: Redis Error Subscriber for TickStockPL Integration

This module implements the Redis subscriber that listens for error messages
from TickStockPL and processes them through the enhanced logging system.

Created: 2025-09-25
Purpose: Cross-system error integration via Redis pub-sub
Architecture: Background thread, auto-reconnect, graceful degradation
"""

import redis
import threading
import json
import time
import logging
from typing import Optional, Callable, Dict, Any

from src.core.services.enhanced_logger import EnhancedLogger
from src.core.services.config_manager import LoggingConfig
from src.core.models.error_models import ErrorMessage


class ErrorSubscriber:
    """Subscribe to TickStockPL errors via Redis pub-sub channel

    This subscriber runs in a background thread and processes error messages
    from TickStockPL, routing them through the enhanced logging system.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        enhanced_logger: EnhancedLogger,
        config: LoggingConfig
    ):
        """Initialize error subscriber

        Args:
            redis_client: Redis client instance
            enhanced_logger: Enhanced logger for processing errors
            config: Logging configuration
        """
        self.redis_client = redis_client
        self.enhanced_logger = enhanced_logger
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Thread control
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.pubsub: Optional[redis.client.PubSub] = None

        # Performance tracking
        self.messages_processed = 0
        self.errors_encountered = 0
        self.last_message_time = None

        # Reconnection settings
        self.reconnect_delay = 5  # Start with 5 seconds
        self.max_reconnect_delay = 60  # Max 60 seconds
        self.reconnect_attempts = 0

    def start(self) -> bool:
        """Start listening for error messages

        Returns:
            bool: True if subscriber started successfully
        """
        if self.running:
            self.logger.warning("Error subscriber is already running")
            return True

        try:
            self.running = True
            self.thread = threading.Thread(target=self._listen, daemon=True)
            self.thread.start()

            self.logger.info(
                f"Error subscriber started for channel: {self.config.redis_error_channel}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to start error subscriber: {e}")
            self.running = False
            return False

    def stop(self):
        """Stop listening for error messages"""
        if not self.running:
            return

        self.running = False

        # Close pubsub connection
        if self.pubsub:
            try:
                self.pubsub.unsubscribe()
                self.pubsub.close()
            except Exception as e:
                self.logger.error(f"Error closing pubsub connection: {e}")

        # Wait for thread to finish
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)

        self.logger.info("Error subscriber stopped")

    def _listen(self):
        """Main listening loop - runs in background thread"""
        while self.running:
            try:
                self._connect_and_listen()

                # If we get here, connection was lost
                if self.running:
                    self._handle_reconnection()

            except Exception as e:
                self.logger.error(f"Unexpected error in listener thread: {e}")
                if self.running:
                    self._handle_reconnection()

    def _connect_and_listen(self):
        """Connect to Redis and listen for messages"""
        try:
            # Create new pubsub connection
            self.pubsub = self.redis_client.pubsub()
            self.pubsub.subscribe(self.config.redis_error_channel)

            self.logger.info(f"Subscribed to Redis channel: {self.config.redis_error_channel}")
            self.reconnect_attempts = 0
            self.reconnect_delay = 5  # Reset delay

            # Listen for messages
            for message in self.pubsub.listen():
                if not self.running:
                    break

                if message['type'] == 'message':
                    self._process_message(message)

        except redis.ConnectionError as e:
            self.logger.error(f"Redis connection error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error in message listening loop: {e}")
            raise
        finally:
            if self.pubsub:
                try:
                    self.pubsub.close()
                except:
                    pass
                self.pubsub = None

    def _process_message(self, message: Dict[str, Any]):
        """Process a single error message from Redis

        Args:
            message: Redis message dictionary
        """
        try:
            self.messages_processed += 1
            self.last_message_time = time.time()

            # Extract message data
            message_data = message['data']

            # Use enhanced logger's Redis message handler
            self.enhanced_logger.log_from_redis_message(message_data)

            # Log processing stats periodically
            if self.messages_processed % 100 == 0:
                self.logger.info(
                    f"Processed {self.messages_processed} error messages from TickStockPL"
                )

        except Exception as e:
            self.errors_encountered += 1
            self.logger.error(f"Failed to process error message from Redis: {e}")

            # Log the raw message for debugging
            try:
                raw_data = message.get('data', b'').decode('utf-8', errors='ignore')
                self.logger.debug(f"Raw message data: {raw_data[:500]}...")  # Truncate long messages
            except:
                pass

    def _handle_reconnection(self):
        """Handle reconnection logic with exponential backoff"""
        if not self.running:
            return

        self.reconnect_attempts += 1

        # Log reconnection attempt
        self.logger.warning(
            f"Attempting to reconnect to Redis (attempt {self.reconnect_attempts}), "
            f"waiting {self.reconnect_delay} seconds..."
        )

        # Wait before reconnecting
        time.sleep(self.reconnect_delay)

        # Exponential backoff with jitter
        self.reconnect_delay = min(
            self.reconnect_delay * 1.5,  # 1.5x multiplier
            self.max_reconnect_delay
        )

        # Test Redis connection
        try:
            self.redis_client.ping()
            self.logger.info("Redis connection restored")
        except Exception as e:
            self.logger.error(f"Redis still not available: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get subscriber statistics

        Returns:
            Dict: Statistics about message processing
        """
        return {
            'running': self.running,
            'messages_processed': self.messages_processed,
            'errors_encountered': self.errors_encountered,
            'reconnect_attempts': self.reconnect_attempts,
            'last_message_time': self.last_message_time,
            'channel': self.config.redis_error_channel
        }

    def health_check(self) -> Dict[str, Any]:
        """Check subscriber health status

        Returns:
            Dict: Health status information
        """
        now = time.time()
        healthy = True
        issues = []

        # Check if running
        if not self.running:
            healthy = False
            issues.append("Subscriber not running")

        # Check for recent activity (if we've processed messages)
        if self.last_message_time and (now - self.last_message_time) > 300:  # 5 minutes
            issues.append("No messages received in 5 minutes")

        # Check error rate
        if self.messages_processed > 0:
            error_rate = self.errors_encountered / self.messages_processed
            if error_rate > 0.1:  # More than 10% errors
                healthy = False
                issues.append(f"High error rate: {error_rate:.2%}")

        # Check Redis connection
        try:
            self.redis_client.ping()
        except Exception as e:
            healthy = False
            issues.append(f"Redis connection failed: {e}")

        return {
            'healthy': healthy,
            'issues': issues,
            'stats': self.get_stats(),
            'check_time': now
        }

    def test_message_processing(self):
        """Send a test message to verify processing works"""
        try:
            # Create test error message
            test_error = ErrorMessage.create(
                source='TickStockPL',
                severity='info',
                message='Test error message from ErrorSubscriber',
                category='test',
                component='ErrorSubscriberTest',
                context={'test': True, 'timestamp': time.time()}
            )

            # Publish test message
            self.redis_client.publish(
                self.config.redis_error_channel,
                test_error.to_json()
            )

            self.logger.info("Test message published to Redis channel")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send test message: {e}")
            return False


def create_error_subscriber(
    redis_client: redis.Redis,
    enhanced_logger: EnhancedLogger,
    config: Optional[LoggingConfig] = None
) -> ErrorSubscriber:
    """Factory function to create error subscriber

    Args:
        redis_client: Redis client instance
        enhanced_logger: Enhanced logger instance
        config: Optional logging configuration

    Returns:
        ErrorSubscriber: Configured error subscriber
    """
    if config is None:
        config = LoggingConfig()

    return ErrorSubscriber(
        redis_client=redis_client,
        enhanced_logger=enhanced_logger,
        config=config
    )


# Global error subscriber instance (will be initialized by app.py)
error_subscriber: Optional[ErrorSubscriber] = None


def get_error_subscriber() -> Optional[ErrorSubscriber]:
    """Get the global error subscriber instance

    Returns:
        ErrorSubscriber: Global error subscriber or None if not initialized
    """
    return error_subscriber


def set_error_subscriber(subscriber: ErrorSubscriber):
    """Set the global error subscriber instance

    Args:
        subscriber: ErrorSubscriber instance to set as global
    """
    global error_subscriber
    error_subscriber = subscriber