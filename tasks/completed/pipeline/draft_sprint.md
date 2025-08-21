Sprint Plan: Multi-Channel Architecture Implementation

Reference:  docs\new\process_tick_pipeline.md contains current pipeline outline. Maintain and update this throughout the sprint. 

# Table of Contents - Sprint Overview
| Sprint | Objective | Key Deliverables |
|--------|-----------|------------------|
| Sprint 103 | Architecture Review & Analysis | Detailed assessment of current system, gap analysis, architectural recommendations |
| Sprint 104 | Multi-Channel Design & Planning | Design new channel architecture, routing strategy, priority queue system |
| Sprint 105 | Core Channel Infrastructure | Implement ProcessingChannel base, ChannelRouter, and priority management |
| Sprint 106 | Data Type Handlers | Create OHLCV, Tick, and FMV specific channel handlers |
| Sprint 107 | Event Processing Refactor | Update event detection for multi-source, implement source-specific rules |
| Sprint 108 | Integration & Testing | Connect all components, performance testing, validation |

Sprint 103: Architecture Review & Analysis
Current Architecture Analysis
Based on the provided files, here's the current linear flow:
RealTimeAdapter → MarketDataService.handle_websocket_tick() → EventProcessor.handle_tick() 
→ EventDetector.detect_events() → Individual Detectors → Priority Queue → Display
Key Findings from Code Review
1. Single Entry Point Bottleneck

All data flows through handle_websocket_tick() regardless of type
No differentiation between tick, OHLCV, or FMV data at entry
Sequential processing creates bottleneck at ~8,000 symbols

2. Tight Coupling Issues
python# In market_data_service.py - Everything goes through one method
def handle_websocket_tick(self, tick_data: TickData, ticker=None, timestamp=None):
    # Single processing path for all data types
    processing_result = self.event_processor.handle_tick(tick_data)
3. Missing Channel Separation

No concept of data channels or parallel processing
EventProcessor treats all data uniformly
Priority management happens after processing, not at routing

4. Current Strengths to Preserve

Clean typed event system (Phase 4)
Working priority queue mechanism
Good universe management structure
Functional event detection logic

# Gap Analysis Matrix
| Component | Current State | Target State | Gap | Priority |
|-----------|---------------|--------------|-----|----------|
| Data Router | None - single entry point | Multi-channel router by data type | Create new component | HIGH |
| Processing Channels | Single linear pipeline | Parallel channels (Tick/OHLCV/FMV) | Create channel abstraction | HIGH |
| Event Detection | Uniform for all sources | Source-specific rules | Add source context | MEDIUM |
| Priority Queue | Post-processing | Pre-routing + post-detection | Enhance existing | MEDIUM |
| Volume Handling | Sequential processing | Parallel with batching | Add batch processing | HIGH |
| Data Persistence | Not implemented | Async batch writer | Deferred to later sprint | LOW |

Architectural Recommendations
1. Create Multi-Channel Entry Point
pythonclass DataChannelRouter:
    """Routes incoming data to appropriate processing channels"""
    
    def route_data(self, data: Union[TickData, OHLCVData, FMVData]):
        data_type = self.identify_data_type(data)
        channel = self.channel_map[data_type]
        return channel.process(data)
2. Implement Processing Channel Abstraction
pythonclass ProcessingChannel:
    def __init__(self, channel_type: str, priority: int):
        self.channel_type = channel_type
        self.priority = priority
        self.event_rules = self.load_event_rules()
        
    async def process(self, data):
        # Channel-specific processing
        pass
3. Refactor Entry Points
Instead of single handle_websocket_tick(), create:

handle_tick_data() - Real-time tick processing
handle_ohlcv_data() - Per-minute aggregate processing
handle_fmv_data() - Fair market value processing


Sprint 104: Multi-Channel Design & Planning
Detailed Channel Architecture Design
Channel Types & Priorities
python@dataclass
class ChannelConfig:
    name: str
    data_type: str
    priority: int  # 1=highest
    batch_size: int
    timeout_ms: int
    event_rules: Dict
    
CHANNEL_CONFIGS = {
    'TICK': ChannelConfig(
        name='RealTimeTick',
        data_type='tick',
        priority=1,
        batch_size=1,  # Process immediately
        timeout_ms=10,
        event_rules={'detect_all': True}
    ),
    'OHLCV': ChannelConfig(
        name='MinuteAggregate', 
        data_type='ohlcv',
        priority=2,
        batch_size=100,  # Batch for efficiency
        timeout_ms=100,
        event_rules={'detect_highs_lows': True, 'detect_trends': False}
    ),
    'FMV': ChannelConfig(
        name='FairMarketValue',
        data_type='fmv',
        priority=3,
        batch_size=50,
        timeout_ms=500,
        event_rules={'custom_fmv_rules': True}
    )
}
New Data Flow Architecture
                    ┌─────────────────┐
                    │  Data Sources   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Channel Router  │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
   ┌────▼────┐          ┌────▼────┐         ┌────▼────┐
   │  TICK   │          │  OHLCV  │         │   FMV   │
   │ Channel │          │ Channel │         │ Channel │
   │ (P1)    │          │ (P2)    │         │ (P3)    │
   └────┬────┘          └────┬────┘         └────┬────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │ Priority Queue   │
                    │   Aggregator     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Event Publisher │
                    └─────────────────┘

Sprint 105: Core Channel Infrastructure Implementation
Task 1: Create Base Channel Class
python# src/processing/channels/base_channel.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import asyncio
import time

@dataclass
class ChannelMetrics:
    messages_processed: int = 0
    messages_failed: int = 0
    avg_processing_time_ms: float = 0
    last_processed: float = 0
    
class ProcessingChannel(ABC):
    def __init__(self, config: ChannelConfig, event_processor):
        self.config = config
        self.event_processor = event_processor
        self.metrics = ChannelMetrics()
        self.processing_queue = asyncio.Queue(maxsize=10000)
        self.batch_buffer = []
        self.last_batch_time = time.time()
        
    @abstractmethod
    async def process_data(self, data: Any) -> Dict:
        """Process data according to channel rules"""
        pass
        
    async def add_to_channel(self, data: Any):
        """Add data to channel queue"""
        await self.processing_queue.put({
            'data': data,
            'timestamp': time.time(),
            'priority': self.config.priority
        })
        
    async def process_batch(self):
        """Process accumulated batch"""
        if not self.batch_buffer:
            return
            
        start_time = time.time()
        results = []
        
        for item in self.batch_buffer:
            result = await self.process_data(item['data'])
            results.append(result)
            
        # Update metrics
        processing_time = (time.time() - start_time) * 1000
        self.metrics.messages_processed += len(self.batch_buffer)
        self.metrics.avg_processing_time_ms = processing_time / len(self.batch_buffer)
        self.metrics.last_processed = time.time()
        
        self.batch_buffer.clear()
        return results
Task 2: Implement Channel Router
python# src/processing/channels/channel_router.py
from typing import Union, Dict
import logging

class DataChannelRouter:
    def __init__(self, config: Dict):
        self.config = config
        self.channels = {}
        self.initialize_channels()
        
    def initialize_channels(self):
        """Initialize all processing channels"""
        from .tick_channel import TickChannel
        from .ohlcv_channel import OHLCVChannel
        from .fmv_channel import FMVChannel
        
        self.channels['tick'] = TickChannel(CHANNEL_CONFIGS['TICK'])
        self.channels['ohlcv'] = OHLCVChannel(CHANNEL_CONFIGS['OHLCV'])
        self.channels['fmv'] = FMVChannel(CHANNEL_CONFIGS['FMV'])
        
    def identify_data_type(self, data) -> str:
        """Identify data type for routing"""
        # Check for OHLCV fields
        if hasattr(data, 'open') and hasattr(data, 'close'):
            return 'ohlcv'
        # Check for FMV indicator
        elif hasattr(data, 'fair_market_value'):
            return 'fmv'
        # Default to tick
        else:
            return 'tick'
            
    async def route_data(self, data):
        """Route data to appropriate channel"""
        data_type = self.identify_data_type(data)
        
        if data_type not in self.channels:
            logging.error(f"Unknown data type: {data_type}")
            return None
            
        channel = self.channels[data_type]
        await channel.add_to_channel(data)
        
        # Process immediately for high priority
        if channel.config.priority == 1:
            return await channel.process_data(data)
        # Batch for lower priority
        else:
            channel.batch_buffer.append({'data': data})
            if len(channel.batch_buffer) >= channel.config.batch_size:
                return await channel.process_batch()

Sprint 106: Data Type Specific Handlers
Task 1: OHLCV Channel Implementation
python# src/processing/channels/ohlcv_channel.py
class OHLCVChannel(ProcessingChannel):
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self.aggregation_window = 60  # seconds
        self.symbol_buffers = {}  # Buffer per symbol
        
    async def process_data(self, data: OHLCVData) -> Dict:
        """Process OHLCV aggregate data"""
        ticker = data.ticker
        
        # Initialize symbol buffer if needed
        if ticker not in self.symbol_buffers:
            self.symbol_buffers[ticker] = []
            
        # Add to buffer
        self.symbol_buffers[ticker].append(data)
        
        # Process if we have enough data points
        if len(self.symbol_buffers[ticker]) >= 5:  # 5 minute window
            return await self.process_aggregates(ticker)
            
        # Quick detection for significant moves
        if abs(data.percent_change) > 2.0:  # 2% move
            return await self.detect_ohlcv_events(data)
            
    async def detect_ohlcv_events(self, data: OHLCVData):
        """Detect events specific to OHLCV data"""
        events = []
        
        # High/Low detection based on OHLCV
        if data.high == data.close:  # Closing at high
            events.append(self.create_high_event(data))
        elif data.low == data.close:  # Closing at low
            events.append(self.create_low_event(data))
            
        # Volume surge detection
        if data.volume > data.avg_volume * 3:
            events.append(self.create_volume_surge_event(data))
            
        return {'events': events, 'ticker': data.ticker}
Task 2: FMV Channel Implementation
python# src/processing/channels/fmv_channel.py
class FMVChannel(ProcessingChannel):
    def __init__(self, config: ChannelConfig):
        super().__init__(config)
        self.fmv_thresholds = {
            'deviation_percent': 1.0,  # 1% deviation triggers event
            'confidence_min': 0.8
        }
        
    async def process_data(self, data: FMVData) -> Dict:
        """Process Fair Market Value data"""
        events = []
        
        # Check deviation from market price
        deviation = abs(data.fmv - data.market_price) / data.market_price * 100
        
        if deviation > self.fmv_thresholds['deviation_percent']:
            event = {
                'type': 'fmv_deviation',
                'ticker': data.ticker,
                'fmv': data.fmv,
                'market_price': data.market_price,
                'deviation_percent': deviation,
                'direction': 'overvalued' if data.fmv > data.market_price else 'undervalued',
                'confidence': data.confidence
            }
            events.append(event)
            
        return {'events': events, 'processed': True}

Sprint 107: Event Processing Refactor
Task 1: Update EventProcessor for Multi-Channel
python# Modifications to event_processor.py
class EventProcessor:
    def __init__(self, config, market_service, event_manager, **kwargs):
        # ... existing init ...
        self.channel_router = DataChannelRouter(config)
        self.source_context = {}  # Track source per ticker
        
    async def handle_multi_source_data(self, data: Any, source: str):
        """New entry point for multi-source data"""
        # Track source context
        if hasattr(data, 'ticker'):
            self.source_context[data.ticker] = source
            
        # Route through channels
        result = await self.channel_router.route_data(data)
        
        # Process events with source context
        if result and 'events' in result:
            for event in result['events']:
                event['source'] = source
                await self.process_with_source_rules(event)
                
    def process_with_source_rules(self, event: Dict):
        """Apply source-specific event rules"""
        source = event.get('source', 'unknown')
        
        if source == 'ohlcv':
            # OHLCV specific rules
            if event['type'] in ['high', 'low']:
                # Only process if significant move
                if abs(event.get('percent_change', 0)) < 1.0:
                    return None
                    
        elif source == 'tick':
            # Real-time tick rules (existing logic)
            pass
            
        elif source == 'fmv':
            # FMV specific rules
            if event.get('confidence', 0) < 0.7:
                return None  # Skip low confidence FMV events
                
        return event
Task 2: Update MarketDataService Entry Points
python# Updates to market_data_service.py
class MarketDataService:
    def __init__(self, config, data_provider, event_manager, **kwargs):
        # ... existing init ...
        self.channel_router = DataChannelRouter(config)
        
    async def handle_ohlcv_data(self, ohlcv_data: OHLCVData):
        """New handler for OHLCV data"""
        try:
            # Update stats
            self.stats.ohlcv_received += 1
            
            # Route through channel system
            result = await self.event_processor.handle_multi_source_data(
                ohlcv_data, 
                source='ohlcv'
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling OHLCV data: {e}")
            
    async def handle_fmv_data(self, fmv_data: FMVData):
        """New handler for FMV data"""
        try:
            # Route through channel system
            result = await self.event_processor.handle_multi_source_data(
                fmv_data,
                source='fmv'
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling FMV data: {e}")

Sprint 108: Integration & Testing
Integration Tasks

Connect New Channels to Existing Pipeline
Update WebSocket handlers for multi-source
Performance testing with 8,000+ symbols
Validate event deduplication across sources

Performance Testing Scenarios
python# Test configuration for load testing
TEST_SCENARIOS = {
    'market_open_surge': {
        'ohlcv_symbols': 8000,
        'tick_symbols': 100,  # High priority tickers
        'events_per_minute': 50000,
        'duration_minutes': 5
    },
    'steady_state': {
        'ohlcv_symbols': 8000,
        'tick_symbols': 500,
        'events_per_minute': 10000,
        'duration_minutes': 30
    }
}
# Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| OHLCV Processing Rate | 8,000 symbols/minute | Channel metrics |
| Tick Latency | < 50ms p99 | Event timestamp tracking |
| Memory Usage | < 2GB for 8k symbols | System monitor |
| Event Deduplication | 100% accuracy | Test validation |
| Channel Isolation | No cross-contamination | Integration tests |


The architecture is designed to:
Support 8,000+ symbols with OHLCV data through batching
Maintain sub-50ms latency for priority tick data
Provide clear separation between data types
Enable future async persistence (marked locations for Sprint X)

This multi-channel approach will transform your linear pipeline into a scalable, parallel processing system while preserving your existing event detection logic and typed event system.