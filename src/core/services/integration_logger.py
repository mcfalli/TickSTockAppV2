"""
Integration Flow Logger
Dedicated logger for tracking data flow through TickStock integration points.

Purpose: Provide clear visibility into the pattern detection pipeline from
TickStockPL events through Redis to WebSocket delivery.
"""

import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any

# Create dedicated integration logger
integration_logger = logging.getLogger('INTEGRATION')
integration_logger.setLevel(logging.INFO)

# Add specific formatter for integration logs
formatter = logging.Formatter(
    '%(asctime)s [INTEGRATION] %(message)s',
    datefmt='%H:%M:%S'
)

# Console handler with special formatting
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
integration_logger.addHandler(console_handler)

# File handler will be added dynamically by configure_integration_logging()
# when INTEGRATION_LOG_FILE=true in .env
# This prevents duplicate log files (integration_flow.log and integration_[timestamp].log)

class IntegrationPoint(Enum):
    """Integration points in the pattern detection pipeline."""
    # TickStockPL → Redis
    PATTERN_DETECTED = "✓ Pattern Detected"
    PATTERN_PUBLISHED = "→ Published to Redis"

    # Redis → TickStockAppV2
    EVENT_RECEIVED = "← Event Received"
    EVENT_PARSED = "✓ Event Parsed"

    # Processing
    USER_FILTER_START = "▶ User Filtering"
    USER_FILTER_RESULT = "✓ Users Selected"

    # WebSocket Delivery
    WEBSOCKET_BROADCAST = "→ WebSocket Broadcast"
    WEBSOCKET_DELIVERED = "✓ Delivered to User"

    # Errors/Warnings
    STRUCTURE_MISMATCH = "⚠ Structure Mismatch"
    FIELD_MISSING = "⚠ Field Missing"
    NO_SUBSCRIBERS = "○ No Subscribers"

    # Database
    DB_QUERY = "↓ Database Query"
    DB_RESULT = "↑ Database Result"

    # Cache
    CACHE_HIT = "● Cache Hit"
    CACHE_MISS = "○ Cache Miss"
    CACHE_UPDATE = "↻ Cache Updated"

@dataclass
class IntegrationEvent:
    """Represents an event flowing through the integration pipeline."""
    symbol: str
    pattern: str
    confidence: float
    timestamp: float
    source: str = "unknown"
    tier: str = "unknown"

    def __str__(self):
        return f"{self.pattern}@{self.symbol} ({self.confidence:.0%})"

class IntegrationFlowLogger:
    """
    Tracks and logs the flow of pattern events through the system.

    Example flow tracking:
        [10:30:45] ✓ Pattern Detected: Hammer@AAPL (85%)
        [10:30:45] → Published to Redis: channel=tickstock.events.patterns
        [10:30:45] ← Event Received: RedisEventSubscriber
        [10:30:45] ✓ Event Parsed: Hammer@AAPL
        [10:30:45] ▶ User Filtering: 45 total users
        [10:30:45] ✓ Users Selected: 12 interested users
        [10:30:45] → WebSocket Broadcast: 12 sessions
        [10:30:45] ✓ Delivered to User: session_abc123
    """

    def __init__(self, enabled: bool = True):
        """Initialize integration flow logger."""
        self.enabled = enabled
        self.flow_id = 0
        self.active_flows = {}

    def is_enabled(self) -> bool:
        """Check if integration logging is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable integration logging."""
        self.enabled = enabled
        integration_logger.info(f"Integration logging {'enabled' if enabled else 'disabled'}")

    def start_flow(self, event_data: dict[str, Any]) -> str:
        """Start tracking a new event flow."""
        if not self.enabled:
            return ""

        self.flow_id += 1
        flow_id = f"flow_{self.flow_id}"

        # Extract event details
        pattern_data = event_data.get('data', event_data)
        if isinstance(pattern_data, dict) and 'data' in pattern_data:
            pattern_data = pattern_data['data']

        event = IntegrationEvent(
            symbol=pattern_data.get('symbol', 'UNKNOWN'),
            pattern=pattern_data.get('pattern') or pattern_data.get('pattern_type', 'UNKNOWN'),
            confidence=pattern_data.get('confidence', 0),
            timestamp=time.time(),
            source=pattern_data.get('source', 'unknown'),
            tier=pattern_data.get('tier', pattern_data.get('source', 'unknown'))
        )

        self.active_flows[flow_id] = {
            'event': event,
            'start_time': time.time(),
            'checkpoints': []
        }

        return flow_id

    def log_checkpoint(self, flow_id: str, point: IntegrationPoint,
                       details: str | None = None):
        """Log a checkpoint in the event flow."""
        if not self.enabled or not flow_id or flow_id not in self.active_flows:
            return

        flow = self.active_flows[flow_id]
        event = flow['event']

        # Build log message
        msg = f"{point.value}: {event}"
        if details:
            msg += f" [{details}]"

        # Log with timing
        elapsed = time.time() - flow['start_time']
        if elapsed > 0.001:  # Show timing if > 1ms
            msg += f" ({elapsed*1000:.1f}ms)"

        integration_logger.info(msg)

        # Track checkpoint
        flow['checkpoints'].append({
            'point': point,
            'time': time.time(),
            'details': details
        })

    def complete_flow(self, flow_id: str):
        """Complete tracking of an event flow."""
        if not self.enabled or not flow_id or flow_id not in self.active_flows:
            return

        flow = self.active_flows.pop(flow_id, None)
        if flow:
            total_time = time.time() - flow['start_time']
            if total_time > 0.1:  # Log slow flows
                integration_logger.warning(
                    f"⚠ Slow flow completed: {flow['event']} took {total_time*1000:.1f}ms"
                )

# Global instance
flow_logger = IntegrationFlowLogger()

def log_integration_point(point: IntegrationPoint, details: str | None = None):
    """Quick logging of integration points without flow tracking."""
    if flow_logger.enabled:
        msg = point.value
        if details:
            msg += f": {details}"
        integration_logger.info(msg)

def integration_checkpoint(point: IntegrationPoint):
    """Decorator for logging integration checkpoints."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if flow_logger.enabled:
                log_integration_point(point, f"Starting {func.__name__}")
            result = func(*args, **kwargs)
            if flow_logger.enabled:
                log_integration_point(point, f"Completed {func.__name__}")
            return result
        return wrapper
    return decorator

# Configuration helper
def configure_integration_logging(enabled: bool = True,
                                 log_file: bool = True,
                                 log_level: str = 'INFO'):
    """
    Configure integration logging settings.

    Args:
        enabled: Enable/disable integration logging
        log_file: Write to separate log file in logs/ folder
        log_level: Logging level (INFO, DEBUG, WARNING)
    """
    flow_logger.set_enabled(enabled)

    # Set log level
    integration_logger.setLevel(getattr(logging, log_level.upper()))

    # Configure file logging
    if log_file:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        # Create log file with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file_path = os.path.join(logs_dir, f'integration_{timestamp}.log')

        # Remove existing file handlers
        for handler in integration_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                integration_logger.removeHandler(handler)

        # Add new file handler
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        integration_logger.addHandler(file_handler)

        integration_logger.info(f"Integration logging to file: {log_file_path}")
    else:
        # Remove file handler if exists
        for handler in integration_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                integration_logger.removeHandler(handler)

    return flow_logger

# Convenience functions for common patterns
def log_pattern_detected(symbol: str, pattern: str, confidence: float, tier: str = "unknown"):
    """Log pattern detection."""
    if flow_logger.enabled:
        integration_logger.info(
            f"✓ Pattern Detected: {pattern}@{symbol} ({confidence:.0%}) [{tier}]"
        )

def log_redis_publish(channel: str, event_type: str):
    """Log Redis publishing."""
    if flow_logger.enabled:
        integration_logger.info(
            f"→ Published to Redis: {event_type} on {channel}"
        )

def log_websocket_delivery(pattern: str, symbol: str, user_count: int):
    """Log WebSocket delivery."""
    if flow_logger.enabled:
        integration_logger.info(
            f"✓ WebSocket Delivered: {pattern}@{symbol} to {user_count} users"
        )

def log_cache_operation(operation: str, key: str, hit: bool = True):
    """Log cache operations."""
    if flow_logger.enabled:
        point = IntegrationPoint.CACHE_HIT if hit else IntegrationPoint.CACHE_MISS
        integration_logger.info(f"{point.value}: {operation} for {key}")

# Usage Example:
"""
from src.core.services.integration_logger import (
    flow_logger, IntegrationPoint, log_pattern_detected,
    log_redis_publish, log_websocket_delivery
)

# In redis_event_subscriber.py
def _handle_pattern_event(self, event):
    flow_id = flow_logger.start_flow(event.data)
    flow_logger.log_checkpoint(flow_id, IntegrationPoint.EVENT_RECEIVED)

    # Process event...
    flow_logger.log_checkpoint(flow_id, IntegrationPoint.EVENT_PARSED)

    # Filter users...
    flow_logger.log_checkpoint(flow_id, IntegrationPoint.USER_FILTER_START, "45 users")
    interested_users = get_interested_users()
    flow_logger.log_checkpoint(flow_id, IntegrationPoint.USER_FILTER_RESULT, f"{len(interested_users)} selected")

    # Broadcast...
    flow_logger.log_checkpoint(flow_id, IntegrationPoint.WEBSOCKET_BROADCAST)
    broadcast_to_users()

    flow_logger.complete_flow(flow_id)
"""
