"""
Multi-channel processing system for TickStock.

This package implements the core channel infrastructure for processing different 
data types (Tick, OHLCV, FMV) through specialized processing channels.

Sprint 105: Core Channel Infrastructure Implementation
Sprint 106: Data Type Handlers - Specialized channel implementations
"""

from .base_channel import (
    ProcessingChannel,
    ChannelType,
    ChannelStatus,
    ProcessingResult
)

from .channel_metrics import (
    ChannelMetrics,
    ChannelHealthStatus,
    MetricsCollector
)

from .channel_config import (
    ChannelConfig,
    BatchingConfig,
    BatchingStrategy,
    ChannelConfigurationManager
)

from .channel_router import (
    DataChannelRouter,
    DataTypeIdentifier,
    ChannelLoadBalancer,
    RouterConfig
)

# Sprint 106: Data Type Handler Channels
from .tick_channel import TickChannel
from .ohlcv_channel import OHLCVChannel
from .fmv_channel import FMVChannel

# Sprint 106: Event Creation Logic
from .event_creators import (
    BaseEventCreator,
    TickEventCreator,
    OHLCVEventCreator,
    FMVEventCreator,
    create_event_creator,
    validate_event_transport_format,
    batch_create_transport_dicts
)

__all__ = [
    # Base channel classes
    'ProcessingChannel',
    'ChannelType', 
    'ChannelStatus',
    'ProcessingResult',
    
    # Metrics system
    'ChannelMetrics',
    'ChannelHealthStatus', 
    'MetricsCollector',
    
    # Configuration system
    'ChannelConfig',
    'BatchingConfig',
    'BatchingStrategy',
    'ChannelConfigurationManager',
    
    # Router system
    'DataChannelRouter',
    'DataTypeIdentifier',
    'ChannelLoadBalancer',
    'RouterConfig',
    
    # Sprint 106: Specialized Channel Implementations
    'TickChannel',
    'OHLCVChannel', 
    'FMVChannel',
    
    # Sprint 106: Event Creation System
    'BaseEventCreator',
    'TickEventCreator',
    'OHLCVEventCreator',
    'FMVEventCreator',
    'create_event_creator',
    'validate_event_transport_format',
    'batch_create_transport_dicts'
]