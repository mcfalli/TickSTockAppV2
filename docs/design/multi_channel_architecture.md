# Multi-Channel Architecture Technical Specifications
**Created:** 2025-01-20 - Sprint 104: Multi-Channel Design & Planning  
**Status:** FINAL DESIGN - Ready for Sprint 105 Implementation

## Executive Summary

This document provides comprehensive technical specifications for implementing the multi-channel processing architecture in TickStock. The design addresses the single entry point bottleneck identified in Sprint 103 while preserving all existing functionality and performance characteristics.

## Architecture Overview

### Current vs Target Architecture

**Current (Linear Pipeline):**
```
Data Source → MarketDataService.handle_websocket_tick() → EventProcessor → Event Detection → Priority Queue
```

**Target (Multi-Channel Pipeline):**
```
Data Sources → DataChannelRouter → ProcessingChannels → Event Generation → Priority Queue Integration
```

### Key Design Principles

1. **Backward Compatibility**: All existing functionality preserved
2. **Performance Preservation**: No performance degradation for existing tick processing
3. **Gradual Rollout**: Feature flags and gradual migration capability
4. **Type Safety**: Strongly typed interfaces and comprehensive validation
5. **Monitoring**: Built-in metrics and health monitoring

## Component Specifications

### 1. ProcessingChannel Interface

#### Abstract Base Class
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import asyncio
import time

class ChannelType(Enum):
    TICK = "tick"
    OHLCV = "ohlcv" 
    FMV = "fmv"

class ChannelStatus(Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"

@dataclass
class ChannelMetrics:
    """Channel performance and health metrics"""
    channel_name: str
    processed_count: int = 0
    error_count: int = 0
    last_processing_time_ms: float = 0.0
    avg_processing_time_ms: float = 0.0
    events_generated: int = 0
    status: ChannelStatus = ChannelStatus.INITIALIZING
    last_activity: float = field(default_factory=time.time)
    backlog_size: int = 0

@dataclass
class ProcessingResult:
    """Result of channel processing operation"""
    success: bool
    events: List[BaseEvent] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ProcessingChannel(ABC):
    """Abstract base class for all data processing channels"""
    
    def __init__(self, name: str, config: 'ChannelConfig'):
        self.name = name
        self.config = config
        self.metrics = ChannelMetrics(channel_name=name)
        self._status = ChannelStatus.INITIALIZING
        
    @abstractmethod
    def get_channel_type(self) -> ChannelType:
        """Return the specific channel type"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize channel resources"""
        pass
    
    @abstractmethod
    def validate_data(self, data: Any) -> bool:
        """Validate incoming data format"""
        pass
    
    @abstractmethod
    async def process_data(self, data: Any) -> ProcessingResult:
        """Process data and return events"""
        pass
    
    @abstractmethod
    async def shutdown(self) -> bool:
        """Shutdown channel and cleanup resources"""
        pass
    
    async def process_with_metrics(self, data: Any) -> ProcessingResult:
        """Process data with automatic metrics tracking"""
        start_time = time.time()
        
        try:
            if not self.validate_data(data):
                return ProcessingResult(
                    success=False,
                    errors=[f"Invalid data format for {self.channel_type.value} channel"]
                )
            
            result = await self.process_data(data)
            processing_time_ms = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time_ms
            
            # Update metrics
            self.metrics.processed_count += 1
            self.metrics.events_generated += len(result.events)
            self.metrics.update_processing_time(processing_time_ms)
            
            if not result.success:
                self.metrics.error_count += 1
                
            return result
            
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            self.metrics.error_count += 1
            
            return ProcessingResult(
                success=False,
                errors=[f"Channel processing error: {str(e)}"],
                processing_time_ms=processing_time_ms
            )
    
    def is_healthy(self) -> bool:
        """Check channel health based on metrics"""
        if self._status == ChannelStatus.ERROR:
            return False
            
        if self.metrics.processed_count > 0:
            error_rate = self.metrics.error_count / self.metrics.processed_count
            if error_rate > 0.1:  # >10% error rate
                return False
        
        if self.metrics.avg_processing_time_ms > 5000:  # >5 seconds
            return False
            
        return True
```

#### Implementation Requirements

**Sprint 105 - Phase 1:**
- Implement `TickChannel` class extending `ProcessingChannel`
- Must process TickData objects and generate HighLowEvent, TrendEvent, SurgeEvent
- Performance requirement: <10ms average processing time
- Integration requirement: Forward events to existing priority_manager

**Future Phases:**
- `OHLCVChannel` for bar data processing (Sprint 107)
- `FMVChannel` for fair market value processing (Sprint 108)

### 2. DataChannelRouter Specification

#### Core Router Implementation
```python
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import asyncio
import time

@dataclass
class RouterMetrics:
    """Router performance metrics"""
    total_routed: int = 0
    routing_errors: int = 0
    avg_routing_time_ms: float = 0.0
    routes_by_type: Dict[str, int] = field(default_factory=dict)
    last_activity: float = field(default_factory=time.time)

class DataTypeIdentifier:
    """Identifies data type from incoming data"""
    
    @staticmethod
    def identify_data_type(data: Any) -> Optional[str]:
        """Identify data type from structure"""
        # TickData identification
        if isinstance(data, TickData):
            return "tick"
        
        # Dictionary-based identification
        if isinstance(data, dict):
            if all(key in data for key in ['open', 'high', 'low', 'close', 'volume']):
                return "ohlcv"
            if any(key in data for key in ['fair_market_value', 'fmv', 'valuation']):
                return "fmv"
            if all(key in data for key in ['ticker', 'price', 'timestamp']):
                return "tick"
        
        # Class name-based identification
        type_name = type(data).__name__.lower()
        if 'tick' in type_name:
            return "tick"
        elif 'ohlcv' in type_name or 'bar' in type_name:
            return "ohlcv"
        elif 'fmv' in type_name or 'valuation' in type_name:
            return "fmv"
        
        return None

class DataChannelRouter:
    """Routes data to appropriate processing channels"""
    
    def __init__(self, config: 'RouterConfig'):
        self.config = config
        self.channels: Dict[ChannelType, List[ProcessingChannel]] = {
            ChannelType.TICK: [],
            ChannelType.OHLCV: [],
            ChannelType.FMV: []
        }
        self.metrics = RouterMetrics()
        self.data_identifier = DataTypeIdentifier()
        self._event_processor = None  # Injected from MarketDataService
        
    def register_channel(self, channel: ProcessingChannel):
        """Register channel for routing"""
        channel_type = channel.channel_type
        if channel_type in self.channels:
            self.channels[channel_type].append(channel)
    
    async def route_data(self, data: Any) -> Optional[ProcessingResult]:
        """Route data to appropriate channel and process"""
        start_time = time.time()
        
        try:
            # Step 1: Identify data type
            data_type = self.data_identifier.identify_data_type(data)
            if not data_type:
                self.metrics.routing_errors += 1
                return None
            
            # Step 2: Determine channel type
            channel_type = self._determine_channel_type(data_type)
            if not channel_type:
                self.metrics.routing_errors += 1
                return None
            
            # Step 3: Select specific channel
            available_channels = self.channels.get(channel_type, [])
            if not available_channels:
                self.metrics.routing_errors += 1
                return None
            
            # Simple selection (first healthy channel for Phase 1)
            selected_channel = None
            for channel in available_channels:
                if channel.is_healthy():
                    selected_channel = channel
                    break
            
            if not selected_channel:
                self.metrics.routing_errors += 1
                return None
            
            # Step 4: Process through selected channel
            result = await selected_channel.process_with_metrics(data)
            
            # Step 5: Update metrics
            routing_time_ms = (time.time() - start_time) * 1000
            self.metrics.total_routed += 1
            self.metrics.routes_by_type[data_type] = self.metrics.routes_by_type.get(data_type, 0) + 1
            
            # Step 6: Forward to existing event system
            if result.success and result.events:
                await self._forward_to_event_system(result.events)
            
            return result
            
        except Exception as e:
            self.metrics.routing_errors += 1
            return ProcessingResult(
                success=False,
                errors=[f"Routing error: {str(e)}"]
            )
    
    def _determine_channel_type(self, data_type: str) -> Optional[ChannelType]:
        """Map data type to channel type"""
        mapping = {
            "tick": ChannelType.TICK,
            "ohlcv": ChannelType.OHLCV,
            "fmv": ChannelType.FMV
        }
        return mapping.get(data_type)
    
    async def _forward_to_event_system(self, events: List[BaseEvent]):
        """Forward events to existing priority manager"""
        if self._event_processor and hasattr(self._event_processor, 'market_service'):
            priority_manager = self._event_processor.market_service.priority_manager
            for event in events:
                priority_manager.add_event(event)
    
    def set_event_processor(self, event_processor):
        """Inject EventProcessor reference"""
        self._event_processor = event_processor
```

#### Implementation Requirements

**Sprint 105 - Phase 1:**
- Implement basic routing with TickData support only
- Simple first-available-channel selection strategy
- Integration with existing priority_manager
- Performance requirement: <5ms routing overhead

**Future Enhancement:**
- Load balancing strategies (round-robin, load-based)
- Custom routing rules
- Circuit breaker pattern for failed channels

### 3. Configuration System Specification

#### Channel Configuration Classes
```python
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import json
from pathlib import Path

class BatchingStrategy(Enum):
    IMMEDIATE = "immediate"
    TIME_BASED = "time_based"
    SIZE_BASED = "size_based"
    HYBRID = "hybrid"

@dataclass
class BatchingConfig:
    """Batching configuration"""
    strategy: BatchingStrategy
    max_batch_size: int = 1
    max_wait_time_ms: int = 100
    overflow_action: str = "drop_oldest"

@dataclass
class ChannelConfig(ABC):
    """Base configuration for all channels"""
    name: str
    enabled: bool = True
    priority: int = 1
    max_concurrent_processing: int = 1
    processing_timeout_ms: int = 1000
    batching: BatchingConfig = field(default_factory=lambda: BatchingConfig(BatchingStrategy.IMMEDIATE))
    detection_parameters: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self):
        """Validate configuration"""
        if self.priority < 1:
            raise ValueError("priority must be >= 1")
        if self.processing_timeout_ms < 100:
            raise ValueError("processing_timeout_ms must be >= 100ms")

@dataclass
class TickChannelConfig(ChannelConfig):
    """Tick channel specific configuration"""
    
    # Event detection settings (from Sprint 103 ConfigManager)
    highlow_detection: Dict[str, Any] = field(default_factory=lambda: {
        'min_price_change': 0.01,
        'min_percent_change': 0.1,
        'cooldown_seconds': 1
    })
    
    trend_detection: Dict[str, Any] = field(default_factory=lambda: {
        'direction_threshold': 0.025,
        'strength_threshold': 0.05,
        'min_data_points': 8
    })
    
    surge_detection: Dict[str, Any] = field(default_factory=lambda: {
        'threshold_multiplier': 0.4,
        'volume_threshold': 3.0,
        'min_data_points': 8
    })
    
    def __post_init__(self):
        # Force immediate processing for tick channels
        self.batching = BatchingConfig(strategy=BatchingStrategy.IMMEDIATE)
        
        # Merge detection parameters
        self.detection_parameters.update({
            'highlow': self.highlow_detection,
            'trend': self.trend_detection,
            'surge': self.surge_detection
        })

class ChannelConfigurationManager:
    """Manages channel configurations with file persistence"""
    
    def __init__(self, config_dir: Path = Path("config/channels")):
        self.config_dir = config_dir
        self.configurations: Dict[str, ChannelConfig] = {}
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def create_channel_config(self, channel_type: ChannelType, **kwargs) -> ChannelConfig:
        """Create channel configuration"""
        if channel_type == ChannelType.TICK:
            return TickChannelConfig(**kwargs)
        else:
            raise ValueError(f"Unsupported channel type: {channel_type}")
    
    def load_configuration(self, config_name: str, channel_type: ChannelType) -> ChannelConfig:
        """Load configuration from file or create default"""
        config_file = self.config_dir / f"{config_name}.json"
        
        if not config_file.exists():
            # Create default configuration
            default_config = self.create_channel_config(channel_type, name=config_name)
            self.save_configuration(config_name, default_config)
            return default_config
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        config = self.create_channel_config(channel_type, **config_data)
        config.validate()
        self.configurations[config_name] = config
        return config
    
    def save_configuration(self, config_name: str, config: ChannelConfig):
        """Save configuration to file"""
        config_file = self.config_dir / f"{config_name}.json"
        config.validate()
        
        with open(config_file, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        
        self.configurations[config_name] = config
```

#### Implementation Requirements

**Sprint 105 - Phase 1:**
- Implement TickChannelConfig with all detection parameters from Sprint 103
- File-based configuration persistence in JSON format
- Configuration validation with meaningful error messages
- Default configuration creation if files don't exist

### 4. Integration Layer Specification

#### MarketDataService Integration
```python
from dataclasses import dataclass
import asyncio
import time

@dataclass
class IntegrationConfig:
    """Integration configuration"""
    enable_multi_channel: bool = False  # Feature flag
    fallback_to_legacy: bool = True
    channel_timeout_ms: float = 100.0
    enable_parallel_processing: bool = False

class MarketDataServiceIntegrator:
    """Integrates multi-channel system with existing MarketDataService"""
    
    def __init__(self, market_data_service, channel_router, config: IntegrationConfig):
        self.market_data_service = market_data_service
        self.channel_router = channel_router
        self.config = config
        
        # Store original handler for fallback
        self._original_tick_handler = market_data_service.handle_websocket_tick
        
        # Set up router connection
        self.channel_router.set_event_processor(market_data_service.event_processor)
        
        # Integration metrics
        self.metrics = {
            'channel_requests': 0,
            'channel_successes': 0,
            'channel_failures': 0,
            'legacy_fallbacks': 0
        }
    
    async def enhanced_handle_websocket_tick(self, tick_data: 'TickData') -> bool:
        """Enhanced tick handler with multi-channel routing"""
        
        # Feature flag check
        if not self.config.enable_multi_channel:
            return await self._call_legacy_handler(tick_data)
        
        self.metrics['channel_requests'] += 1
        
        try:
            # Process through channel router with timeout
            processing_task = asyncio.create_task(
                self.channel_router.route_data(tick_data)
            )
            
            result = await asyncio.wait_for(
                processing_task,
                timeout=self.config.channel_timeout_ms / 1000.0
            )
            
            if result and result.success:
                self.metrics['channel_successes'] += 1
                return True
            else:
                return await self._fallback_to_legacy(tick_data)
                
        except asyncio.TimeoutError:
            return await self._fallback_to_legacy(tick_data)
        except Exception:
            return await self._fallback_to_legacy(tick_data)
    
    async def _fallback_to_legacy(self, tick_data):
        """Fallback to original processing"""
        if self.config.fallback_to_legacy:
            self.metrics['legacy_fallbacks'] += 1
            self.metrics['channel_failures'] += 1
            return await self._call_legacy_handler(tick_data)
        return False
    
    async def _call_legacy_handler(self, tick_data):
        """Call original tick handler"""
        if asyncio.iscoroutinefunction(self._original_tick_handler):
            return await self._original_tick_handler(tick_data)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._original_tick_handler, tick_data)
    
    def install_integration(self):
        """Install integration by replacing tick handler"""
        self.market_data_service.handle_websocket_tick = self.enhanced_handle_websocket_tick
    
    def uninstall_integration(self):
        """Restore original tick handler"""
        self.market_data_service.handle_websocket_tick = self._original_tick_handler
```

#### Implementation Requirements

**Sprint 105 - Phase 1:**
- Install integration layer with multi-channel disabled by default
- Implement timeout protection and fallback to legacy system
- Preserve all existing functionality and performance
- Add comprehensive integration metrics

**Sprint 106 - Phase 2:**
- Enable parallel processing mode for comparison testing
- Implement gradual rollout manager
- Add monitoring and alerting for integration health

## Implementation Guidelines

### Development Standards

#### Code Quality Requirements
- **Test Coverage**: >90% unit test coverage for all channel components
- **Type Safety**: Full type hints for all public methods and classes
- **Documentation**: Comprehensive docstrings following Google style
- **Performance**: All channel processing <10ms average latency
- **Error Handling**: Comprehensive error handling with meaningful messages

#### Coding Patterns
```python
# Preferred async pattern for channel processing
async def process_data(self, data: TickData) -> ProcessingResult:
    """Process tick data and generate events"""
    try:
        # Validation
        if not self.validate_data(data):
            return ProcessingResult(success=False, errors=["Invalid data"])
        
        # Processing logic
        events = []
        
        # High/Low detection
        if self.config.detection_parameters['highlow']['enabled']:
            highlow_events = await self._detect_highlow(data)
            events.extend(highlow_events)
        
        # Return success result
        return ProcessingResult(success=True, events=events)
        
    except Exception as e:
        logger.error(f"Channel processing error: {e}", exc_info=True)
        return ProcessingResult(success=False, errors=[str(e)])

# Preferred error handling pattern
class ChannelProcessingError(Exception):
    """Channel-specific processing error"""
    
    def __init__(self, message: str, channel_name: str, data_type: str):
        self.message = message
        self.channel_name = channel_name
        self.data_type = data_type
        super().__init__(f"Channel {channel_name} ({data_type}): {message}")
```

#### Testing Requirements
```python
import pytest
import asyncio
from unittest.mock import Mock, patch

class TestTickChannel:
    """Test tick channel implementation"""
    
    @pytest.fixture
    def tick_channel(self):
        config = TickChannelConfig(name="test_tick")
        return TickChannel(config)
    
    @pytest.mark.asyncio
    async def test_process_valid_tick_data(self, tick_channel):
        """Test processing valid tick data"""
        tick_data = TickData(ticker="AAPL", price=150.0, timestamp=time.time())
        
        result = await tick_channel.process_data(tick_data)
        
        assert result.success is True
        assert len(result.events) >= 0  # May or may not generate events
        assert result.processing_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_process_invalid_data(self, tick_channel):
        """Test processing invalid data"""
        invalid_data = {"invalid": "data"}
        
        result = await tick_channel.process_data(invalid_data)
        
        assert result.success is False
        assert len(result.errors) > 0
    
    def test_channel_health_monitoring(self, tick_channel):
        """Test channel health status"""
        # Fresh channel should be healthy
        assert tick_channel.is_healthy() is True
        
        # Simulate high error rate
        tick_channel.metrics.processed_count = 100
        tick_channel.metrics.error_count = 20  # 20% error rate
        
        assert tick_channel.is_healthy() is False
```

### Performance Requirements

#### Latency Targets
- **Tick Channel Processing**: <10ms average, <50ms 99th percentile
- **Router Overhead**: <5ms additional latency
- **Integration Layer**: <2ms additional latency
- **End-to-End**: Maintain <100ms from data source to event emission

#### Throughput Targets
- **Tick Channel**: >1000 tickers/second sustained
- **Router**: >4000 routing decisions/second
- **Memory Usage**: <10% increase from baseline
- **CPU Usage**: <5% increase under normal load

#### Monitoring Metrics
```python
# Key metrics to monitor during implementation
CHANNEL_METRICS = {
    'processing_time_ms': 'histogram',
    'processed_count': 'counter', 
    'error_count': 'counter',
    'events_generated': 'counter',
    'channel_health': 'gauge'
}

ROUTER_METRICS = {
    'routing_time_ms': 'histogram',
    'routes_by_type': 'counter',
    'routing_errors': 'counter',
    'channel_selection_time_ms': 'histogram'
}

INTEGRATION_METRICS = {
    'channel_vs_legacy_latency': 'histogram',
    'fallback_rate': 'gauge',
    'integration_success_rate': 'gauge'
}
```

## File Structure for Implementation

### New Files to Create
```
src/processing/channels/
├── __init__.py                     # Channel package initialization
├── base_channel.py                 # ProcessingChannel abstract base class
├── tick_channel.py                 # TickChannel implementation
├── channel_router.py               # DataChannelRouter implementation
├── channel_config.py               # Configuration classes
├── channel_metrics.py              # Metrics and monitoring
└── channel_integration.py          # MarketDataService integration

config/channels/                    # Channel configuration files
├── default_tick.json               # Default tick channel config
└── production_tick.json            # Production tick channel config

tests/unit/channels/                # Channel unit tests
├── test_base_channel.py
├── test_tick_channel.py
├── test_channel_router.py
├── test_channel_config.py
└── test_integration.py

docs/design/                        # Design documentation
├── multi_channel_architecture.md   # This document
├── channel_specifications.md       # Detailed channel specs
└── integration_patterns.md         # Integration documentation
```

### Modified Files
```
src/core/services/market_data_service.py  # Integration point modification
src/processing/pipeline/event_processor.py  # Router connection
```

## Success Criteria

### Sprint 105 Completion Criteria
- [ ] All channel interface classes implemented and tested
- [ ] TickChannel processes real market data successfully
- [ ] Configuration system handles all tick detection parameters
- [ ] Router correctly identifies and routes tick data
- [ ] Integration layer installed with feature flags disabled
- [ ] Performance tests show no degradation with integration disabled
- [ ] >90% test coverage for all new components

### Sprint 106 Completion Criteria  
- [ ] Feature flag enables multi-channel processing successfully
- [ ] Parallel processing mode provides accurate performance comparison
- [ ] 1% gradual rollout maintains system stability
- [ ] All existing event detection functionality preserved
- [ ] Error rate <1% during testing period
- [ ] Performance within 5% of legacy system

---

*This technical specification provides the complete blueprint for implementing the multi-channel architecture while preserving TickStock's high-performance characteristics and ensuring zero-downtime deployment.*