"""
Redis Message Monitor Service
Sprint 43: Debug Redis communication between TickStockPL and TickStockAppV2

Captures ALL Redis pub-sub messages with full structure logging for debugging.
"""

import json
import logging
import time
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class RedisMonitor:
    """
    Monitor and log all Redis pub-sub messages for debugging.

    Features:
    - Captures all messages from all subscribed channels
    - Logs message structure and field names
    - Provides real-time feed via WebSocket
    - Stores recent messages for analysis
    """

    def __init__(self, max_messages: int = 500):
        """
        Initialize Redis monitor.

        Args:
            max_messages: Maximum number of messages to keep in memory
        """
        self.messages = deque(maxlen=max_messages)
        self.lock = Lock()
        self.stats = {
            'total_messages': 0,
            'by_channel': {},
            'by_type': {},
            'start_time': time.time()
        }

        # Field name tracking for debugging
        self.field_names_seen = {
            'patterns': set(),
            'indicators': set()
        }

    def capture_message(self, channel: str, message_data: Dict[str, Any],
                       event_type: str = None):
        """
        Capture a Redis message for monitoring.

        Args:
            channel: Redis channel name
            message_data: Parsed message data
            event_type: Type of event (if known)
        """
        with self.lock:
            timestamp = datetime.now()

            # Analyze message structure
            structure = self._analyze_structure(message_data)

            # Track field names
            if 'detection' in message_data:
                self.field_names_seen['patterns'].update(
                    message_data['detection'].keys()
                )
            if 'calculation' in message_data:
                self.field_names_seen['indicators'].update(
                    message_data['calculation'].keys()
                )

            # Create log entry
            entry = {
                'id': self.stats['total_messages'],
                'timestamp': timestamp.isoformat(),
                'timestamp_unix': timestamp.timestamp(),
                'channel': channel,
                'event_type': event_type or message_data.get('type', 'unknown'),
                'data': message_data,
                'structure': structure,
                'raw_json': json.dumps(message_data, indent=2)
            }

            self.messages.append(entry)

            # Update stats
            self.stats['total_messages'] += 1
            self.stats['by_channel'][channel] = self.stats['by_channel'].get(channel, 0) + 1
            event_type_key = entry['event_type']
            self.stats['by_type'][event_type_key] = self.stats['by_type'].get(event_type_key, 0) + 1

            # Log to console
            logger.info(
                f"REDIS-MONITOR [{channel}] {entry['event_type']}: "
                f"{structure.get('summary', 'No summary')}"
            )

    def _analyze_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze message structure and extract key information.

        Args:
            data: Message data dictionary

        Returns:
            Structure analysis dict
        """
        analysis = {
            'top_level_keys': list(data.keys()),
            'nested_keys': {},
            'summary': ''
        }

        # Check for detection (patterns)
        if 'detection' in data:
            detection = data['detection']
            analysis['nested_keys']['detection'] = list(detection.keys())

            # Extract pattern info
            pattern_field = None
            for field in ['pattern', 'pattern_type', 'pattern_name']:
                if field in detection:
                    pattern_field = field
                    break

            symbol = detection.get('symbol', 'N/A')
            pattern = detection.get(pattern_field, 'N/A') if pattern_field else 'N/A'
            confidence = detection.get('confidence', 0)

            analysis['summary'] = f"Pattern: {pattern} on {symbol} ({confidence:.2f})"
            analysis['pattern_field_name'] = pattern_field

        # Check for calculation (indicators)
        elif 'calculation' in data:
            calculation = data['calculation']
            analysis['nested_keys']['calculation'] = list(calculation.keys())

            # Extract indicator info
            indicator_field = None
            for field in ['indicator', 'indicator_type', 'indicator_name']:
                if field in calculation:
                    indicator_field = field
                    break

            symbol = calculation.get('symbol', 'N/A')
            indicator = calculation.get(indicator_field, 'N/A') if indicator_field else 'N/A'
            value = calculation.get('value', 'N/A')

            analysis['summary'] = f"Indicator: {indicator} on {symbol} = {value}"
            analysis['indicator_field_name'] = indicator_field

        # Other event types
        else:
            event_type = data.get('type', 'unknown')
            analysis['summary'] = f"Event: {event_type}"

        return analysis

    def get_recent_messages(self, limit: int = 50,
                           channel_filter: str = None,
                           type_filter: str = None) -> List[Dict[str, Any]]:
        """
        Get recent messages with optional filtering.

        Args:
            limit: Maximum number of messages to return
            channel_filter: Filter by channel name (partial match)
            type_filter: Filter by event type

        Returns:
            List of message entries
        """
        with self.lock:
            messages = list(self.messages)

        # Apply filters
        if channel_filter:
            messages = [m for m in messages if channel_filter in m['channel']]
        if type_filter:
            messages = [m for m in messages if type_filter in m['event_type']]

        # Return most recent first
        return list(reversed(messages[-limit:]))

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        with self.lock:
            runtime = time.time() - self.stats['start_time']

            return {
                **self.stats,
                'runtime_seconds': round(runtime, 1),
                'messages_per_second': round(self.stats['total_messages'] / max(runtime, 1), 2),
                'field_names_seen': {
                    'patterns': list(self.field_names_seen['patterns']),
                    'indicators': list(self.field_names_seen['indicators'])
                }
            }

    def get_field_name_report(self) -> Dict[str, Any]:
        """
        Generate report on field naming inconsistencies.

        Returns:
            Field name analysis report
        """
        with self.lock:
            pattern_fields = self.field_names_seen['patterns']
            indicator_fields = self.field_names_seen['indicators']

        # Check for multiple pattern field variations
        pattern_name_fields = [f for f in pattern_fields
                              if 'pattern' in f.lower()]
        indicator_name_fields = [f for f in indicator_fields
                                if 'indicator' in f.lower()]

        return {
            'patterns': {
                'all_fields': list(pattern_fields),
                'name_field_variations': pattern_name_fields,
                'has_inconsistency': len(pattern_name_fields) > 1
            },
            'indicators': {
                'all_fields': list(indicator_fields),
                'name_field_variations': indicator_name_fields,
                'has_inconsistency': len(indicator_name_fields) > 1
            },
            'recommendation': self._get_standardization_recommendation(
                pattern_name_fields, indicator_name_fields
            )
        }

    def _get_standardization_recommendation(self,
                                           pattern_fields: List[str],
                                           indicator_fields: List[str]) -> str:
        """Generate standardization recommendation."""
        if len(pattern_fields) > 1 or len(indicator_fields) > 1:
            return (
                "⚠️ INCONSISTENCY DETECTED: Multiple field name variations found. "
                "Recommend standardizing to: 'pattern_type' for patterns, "
                "'indicator_type' for indicators across entire system."
            )
        return "✅ Field naming is consistent across messages."

    def clear(self):
        """Clear all captured messages and reset stats."""
        with self.lock:
            self.messages.clear()
            self.stats = {
                'total_messages': 0,
                'by_channel': {},
                'by_type': {},
                'start_time': time.time()
            }
            self.field_names_seen = {
                'patterns': set(),
                'indicators': set()
            }
