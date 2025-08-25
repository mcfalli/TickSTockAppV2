"""
Multi-channel processing system - SIMPLIFIED (Phase 5 Cleanup)

Simplified channel infrastructure maintaining essential tick processing.
Complex multi-channel routing and metrics removed.
"""

from .base_channel import (
    ProcessingChannel,
    ChannelType,
    ChannelStatus,
    ProcessingResult
)

from .channel_config import (
    ChannelConfig,
    BatchingConfig,
    BatchingStrategy,
    ChannelConfigurationManager
)

# Essential tick processing channel
from .tick_channel import TickChannel

# Complex components removed in Phase 5 cleanup:
# - ChannelMetrics, MetricsCollector (channel_metrics.py)
# - DataChannelRouter, ChannelLoadBalancer (channel_router.py)
# - OHLCVChannel, FMVChannel (ohlcv_channel.py, fmv_channel.py)
# - EventCreator system (event_creators.py)

__all__ = [
    # Base channel classes
    'ProcessingChannel',
    'ChannelType', 
    'ChannelStatus',
    'ProcessingResult',
    
    # Configuration system
    'ChannelConfig',
    'BatchingConfig',
    'BatchingStrategy',
    'ChannelConfigurationManager',
    
    # Essential tick processing
    'TickChannel'
]