"""
Multi-channel processing system for TickStock.

This package implements the core channel infrastructure for processing different 
data types (Tick, OHLCV, FMV) through specialized processing channels.

Sprint 105: Core Channel Infrastructure Implementation
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
    'RouterConfig'
]