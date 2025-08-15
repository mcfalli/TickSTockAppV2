# utils/__init__.py
"""Utility modules for TickStock"""

from src.shared.utils.event_factory import EventFactory
# Phase 4: MigrationHelper removed - no backward compatibility
# Phase 4: compatibility.py DELETED - no backward compatibility utilities
# Phase 4: conversion.py DELETED - no dict conversion utilities

from src.shared.utils.utils import (
    get_eastern_time,
    detect_market_status,
    format_price,
    calculate_percentage_change,
    safe_divide,
    exponential_moving_average,
    rate_limiter,
    retry_with_backoff,
    sanitize_float,
    sanitize_dict,
    generate_event_key,
    # Import any other functions/classes from src.shared.utils.py that are used elsewhere
)

__all__ = [
    'EventFactory',
    # Phase 4: 'MigrationHelper' removed
    # Phase 4: 'TypeConverter' removed
    # Phase 4: 'BatchConverter' removed
    # Phase 4: 'ensure_dict_format' removed
    # Phase 4: 'ensure_typed_format' removed
    # Phase 4: 'process_mixed_events' removed
    'get_eastern_time',
    'detect_market_status',
    'format_price',
    'calculate_percentage_change',
    'safe_divide',
    'exponential_moving_average',
    'rate_limiter',
    'retry_with_backoff',
    'sanitize_float',
    'sanitize_dict',
    'generate_event_key',
    # Add any other exports here
]