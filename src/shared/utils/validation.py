# utils/validation.py
"""General validation utilities"""

import logging
import re
from typing import Any

# Add this import
from src.core.domain.events import BaseEvent, SurgeEvent, TrendEvent

logger = logging.getLogger(__name__)


def validate_ticker(ticker: str) -> bool:
    """Validate ticker symbol format"""
    if not ticker or not isinstance(ticker, str):
        return False
    # Basic validation: 1-5 uppercase letters
    return bool(re.match(r'^[A-Z]{1,5}$', ticker.strip()))

def validate_price(price: float) -> bool:
    """Validate price is positive number"""
    try:
        return float(price) > 0
    except (TypeError, ValueError):
        return False

def validate_timestamp(timestamp: int | float) -> bool:
    """Validate timestamp is reasonable"""
    try:
        ts = float(timestamp)
        # Check if timestamp is within reasonable range (2020-2030)
        return 1577836800 < ts < 1893456000
    except (TypeError, ValueError):
        return False

def validate_event_type(event_type: str) -> bool:
    """Validate event type is recognized"""
    valid_types = [
        'high', 'low', 'session_high', 'session_low',
        'trend', 'surge'
    ]
    return event_type in valid_types

def validate_strength(strength: str) -> bool:
    """Validate strength value"""
    valid_strengths = ['weak', 'moderate', 'strong', 'extreme']
    return strength in valid_strengths

def validate_direction(direction: str) -> bool:
    """Validate direction value"""
    valid_directions = ['up', 'down', '^', 'v']
    return direction in valid_directions

class FieldValidator:
    """Validate fields meet expected criteria"""

    @staticmethod
    def validate_required_fields(data: dict[str, Any],
                               required: list[str]) -> list[str]:
        """Check all required fields are present"""
        missing = []
        for field in required:
            if field not in data or data[field] is None:
                missing.append(field)
        return missing

    @staticmethod
    def validate_field_types(data: dict[str, Any],
                           type_map: dict[str, type]) -> list[str]:
        """Check fields have correct types"""
        errors = []
        for field, expected_type in type_map.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    errors.append(
                        f"{field}: expected {expected_type.__name__}, "
                        f"got {type(data[field]).__name__}"
                    )
        return errors


class EventValidator:
    """Validate events meet S18/19/20 specifications"""

    @staticmethod
    def validate_event_structure(event: BaseEvent) -> list[str]:
        """
        Validate event has proper structure.
        Returns list of validation errors (empty if valid).
        """
        errors = []

        # Check required base fields
        required_fields = ['ticker', 'type', 'price', 'time']
        for field in required_fields:
            if not hasattr(event, field) or getattr(event, field) is None:
                errors.append(f"Missing required field: {field}")

        # Check price validity
        if hasattr(event, 'price') and event.price <= 0:
            errors.append(f"Invalid price: {event.price}")

        # Check type-specific fields
        if isinstance(event, TrendEvent):
            if event.trend_strength not in ['weak', 'moderate', 'strong', 'extreme']:
                errors.append(f"Invalid trend strength: {event.trend_strength}")

        elif isinstance(event, SurgeEvent):
            if event.surge_strength not in ['weak', 'moderate', 'strong', 'extreme']:
                errors.append(f"Invalid surge strength: {event.surge_strength}")

        return errors

    @staticmethod
    def validate_transport_dict(data: dict[str, Any], event_type: str) -> list[str]:
        """Validate dictionary meets S18/19/20 transport spec"""
        errors = []

        # Check for event_specific_data
        if 'event_specific_data' not in data:
            errors.append("Missing event_specific_data field")

        # Check type-specific requirements
        if event_type == 'trend' and 'event_specific_data' in data:
            specific = data['event_specific_data']
            if 'trend_strength' not in specific:
                errors.append("Missing trend_strength in event_specific_data")

        return errors

class DataFlowValidator:
    """Validate data flow through the pipeline"""

    def __init__(self):
        self.checkpoints = {}

    def checkpoint(self, name: str, data: Any):
        """Record data at a checkpoint"""
        self.checkpoints[name] = {
            'data': data,
            'type': type(data).__name__,
            'valid': self._is_valid(data)
        }

    def _is_valid(self, data: Any) -> bool:
        """Check if data is valid"""
        if isinstance(data, BaseEvent):
            return len(EventValidator.validate_event_structure(data)) == 0
        if isinstance(data, dict):
            return 'ticker' in data  # Basic check
        return True

    def get_flow_report(self) -> dict[str, Any]:
        """Get report of data flow"""
        return {
            'checkpoints': list(self.checkpoints.keys()),
            'valid_count': sum(1 for cp in self.checkpoints.values() if cp['valid']),
            'total_count': len(self.checkpoints),
            'details': self.checkpoints
        }
