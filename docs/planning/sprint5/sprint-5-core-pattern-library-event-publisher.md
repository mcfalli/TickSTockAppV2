# TickStock.ai Sprint 5: Core Pattern Library & Event Publisher

## Sprint Overview

**Sprint Duration:** 1 week (5 days)  
**Phase:** Phase 3: Implementation (Sprints 5-7)  
**Sprint Goal:** Implement BasePattern foundation and 3-5 core candlestick patterns plus EventPublisher for Redis pub-sub to establish the foundational pattern detection and event publishing pipeline.

## Objectives

**Primary Objective:** Implement BasePattern and 3-5 candlesticks (e.g., Doji, Hammer); add EventPublisher for Redis.  
**Goal:** Establish foundational detection and publishing for quick signal testing.  
**Outcome:** Code in src/patterns/ and src/analysis/; basic publish demo.  
**Success Metrics:** Working pattern detection with <50ms latency, Redis event publishing, extensible architecture

## Sprint Status Context

**Completed Prerequisites:**
- ✅ Sprint 1: Architecture & Requirements Definition
- ✅ Sprint 2: Pattern Classes & Specifications Design  
- ✅ Sprint 3: Database Schema & Data Flow Architecture
- ✅ Sprint 4: TickStockApp Cleanup & Refactoring

**Current Sprint:** Sprint 5: Core Pattern Library & Event Publisher  
**Next Sprint:** Sprint 6: Pattern Scanner & Event Subscriber

## Key Deliverables

### 1. Core Pattern Infrastructure
- **BasePattern Abstract Class** (`src/patterns/base.py`)
  - Abstract detect() method returning boolean pandas Series
  - Parameter handling system for pattern customization
  - Timeframe support and metadata
  - Type hints and comprehensive docstrings

- **Candlestick Pattern Module** (`src/patterns/candlestick.py`)
  - Concrete implementations of candlestick patterns
  - Shared utility functions for candlestick calculations
  - Parameter validation and edge case handling

### 2. Core Pattern Implementations

**Priority 1 (Must Have):**
- **Doji Pattern**
  - Neutral reversal pattern detection
  - Configurable tolerance parameter
  - Supports User Story 1: real-time detection alerts
  - Event metadata: `{"pattern": "Doji", "symbol": "AAPL", "timestamp": "...", "price": close, "timeframe": "1min"}`

- **Hammer Pattern**  
  - Bullish reversal candlestick pattern
  - Configurable shadow_ratio parameter
  - Direction indication in event output
  - Event metadata includes bullish direction flag

- **EventPublisher System** (`src/analysis/events.py`)
  - Redis pub-sub integration on "tickstock_patterns" channel
  - JSON event serialization with pattern metadata
  - Fallback console logging for development
  - Error handling for Redis connectivity issues

**Priority 2 (Should Have):**
- **ClosedInTop10Percent Pattern**
  - Intraday bullish momentum signal
  - Session-aware detection (market hours only)
  - Configurable percentage threshold

- **ClosedInBottom10Percent Pattern**
  - Intraday bearish momentum signal  
  - Session-aware detection (market hours only)
  - Configurable percentage threshold

### 3. Scanner Integration Foundation
- **PatternScanner Class** (`src/analysis/scanner.py`)
  - add_pattern() method for extensible pattern registration
  - Basic scanning workflow: DataFrame → detect → events
  - Integration with EventPublisher for automatic event publishing
  - Support for multiple patterns on same dataset

### 4. Testing & Validation
- **Unit Test Suite**
  - Pattern-specific tests with sample OHLCV data
  - Parameter validation testing
  - Edge case handling verification
  - >80% code coverage target

- **Integration Tests**
  - End-to-end pattern detection workflow
  - Redis event publishing verification
  - PatternScanner integration validation

- **Performance Benchmarking**
  - Pattern detection latency testing (<50ms requirement)
  - Memory usage profiling
  - Scalability testing with multiple patterns

## Daily Implementation Schedule

### Day 1: Foundation & BasePattern
**Focus:** Core architecture and abstract base classes

**Tasks:**
- Create `src/patterns/` directory structure
- Implement BasePattern abstract class in `src/patterns/base.py`
- Design parameter system for pattern customization
- Set up type hints and docstring standards
- Create initial unit tests for BasePattern
- Validate abstract class enforcement

**Deliverables:**
- Working BasePattern with detect() method signature
- Parameter handling system
- Initial test framework setup

### Day 2: Core Pattern Implementation - Part 1  
**Focus:** Essential candlestick patterns

**Tasks:**
- Implement Doji pattern with tolerance parameter
- Implement Hammer pattern with shadow_ratio parameter
- Add timeframe support and parameter scaling
- Create shared candlestick utility functions
- Implement pattern parameter validation
- Unit tests for Doji and Hammer patterns

**Deliverables:**
- Working Doji and Hammer pattern classes
- Shared utility functions in candlestick module
- Comprehensive unit tests with sample data

### Day 3: EventPublisher & Integration
**Focus:** Event publishing and Redis integration

**Tasks:**
- Implement EventPublisher class for Redis pub-sub
- Design event JSON structure and metadata
- Add Redis connectivity with fallback logging
- Create PatternScanner class foundation
- Implement add_pattern() method
- Basic end-to-end integration testing

**Deliverables:**
- Working EventPublisher with Redis integration
- PatternScanner foundation with pattern registration
- Integration test suite

### Day 4: Scanner Workflow & Additional Patterns
**Focus:** Complete scanning workflow and remaining patterns

**Tasks:**
- Complete PatternScanner implementation
- Implement scanning workflow (DataFrame → detect → events)
- Add ClosedInTop10Percent and ClosedInBottom10Percent patterns
- Session-aware detection for intraday patterns
- Performance optimization and benchmarking
- Integration tests for complete workflow

**Deliverables:**
- Complete PatternScanner with scanning workflow
- All 4 core patterns implemented and tested
- Performance benchmarking results

### Day 5: Demo, Documentation & Sprint Wrap-up
**Focus:** Documentation, examples, and sprint completion

**Tasks:**
- Create demo script in `examples/basic_pattern_demo.py`
- Update pattern documentation with implementation details
- Performance validation against <50ms requirement
- Code review and refactoring for maintainability
- Sprint retrospective and documentation updates
- Prepare handoff to Sprint 6

**Deliverables:**
- Working demo script showing end-to-end detection
- Updated documentation
- Sprint completion report
- Sprint 6 preparation notes

## Technical Implementation Details

### BasePattern Architecture
```python
# src/patterns/base.py
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any, Optional

class BasePattern(ABC):
    """Abstract base class for all pattern implementations."""
    
    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = params or {}
        self.timeframe = self.params.get('timeframe', 'daily')
        self.pattern_name = self.__class__.__name__
        
    @abstractmethod
    def detect(self, data: pd.DataFrame) -> pd.Series:
        """
        Detect pattern occurrences in OHLCV data.
        
        Args:
            data: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            
        Returns:
            Boolean Series indicating pattern detection at each timestamp
        """
        pass
    
    def validate_params(self) -> bool:
        """Validate pattern parameters."""
        pass
    
    def get_event_metadata(self, symbol: str, timestamp: str, price: float) -> Dict[str, Any]:
        """Generate event metadata for pattern detection."""
        pass
```

### Event Structure Standard
```json
{
    "pattern": "Doji",
    "symbol": "AAPL", 
    "timestamp": "2025-08-25T14:30:00Z",
    "price": 150.25,
    "timeframe": "1min",
    "direction": "neutral",
    "metadata": {
        "tolerance": 0.01,
        "candle_range": 2.50,
        "body_size": 0.15
    }
}
```

### Redis Integration
- **Channel:** "tickstock_patterns"
- **Connection:** Redis URL from environment variable
- **Fallback:** Console logging when Redis unavailable
- **Error Handling:** Graceful degradation with retry logic

## User Story Alignment

### Direct User Story Support
- **User Story 1:** Doji real-time detection foundation for trader alerts
- **User Story 2:** BasePattern extensibility enables easy pattern addition by developers
- **User Story 5:** Parameter customization system supports trader tuning requirements
- **User Story 8:** Multi-timeframe support through timeframe parameter and scaling
- **User Story 9:** Foundation architecture supports future composite pattern development

### Indirect Preparation
- **User Story 3:** EventPublisher prepares for historical/live data blending in Sprint 6
- **User Story 4:** Pattern foundation enables backtesting implementation in Sprint 7
- **User Story 6:** Modular architecture supports data source flexibility
- **User Story 10:** Event structure prepares for visualization integration

## Success Criteria & Acceptance

### Functional Requirements
- ✅ BasePattern abstract class enforces detect() method implementation
- ✅ Minimum 3 candlestick patterns (Doji, Hammer, + 1 intraday) working correctly
- ✅ EventPublisher successfully publishes pattern events to Redis
- ✅ PatternScanner can register multiple patterns and scan DataFrames
- ✅ All patterns support parameter customization

### Technical Requirements  
- ✅ Pattern detection latency <50ms on sample datasets
- ✅ Unit test coverage >80% for all implemented components
- ✅ Integration tests verify end-to-end workflow
- ✅ Redis pub-sub integration working with fallback logging
- ✅ Type hints and docstrings for all public methods

### Quality Requirements
- ✅ Code follows TickStock coding standards (see CLAUDE.md)
- ✅ Comprehensive error handling and edge case management
- ✅ Performance benchmarking completed and documented
- ✅ Demo script successfully demonstrates pattern detection workflow

## Risk Management

### Identified Risks
1. **Redis Connectivity Issues**
   - Mitigation: Fallback console logging, environment-based configuration
   
2. **Pattern Accuracy Validation**
   - Mitigation: Comprehensive unit tests with known sample data
   
3. **Performance Requirements (<50ms)**
   - Mitigation: Early benchmarking, vectorized pandas operations
   
4. **Parameter System Complexity**
   - Mitigation: Start simple, iterate based on pattern needs

### Contingency Plans
- If Redis integration fails: Complete with console logging fallback
- If performance issues arise: Focus on core 3 patterns, optimize in Sprint 6
- If pattern accuracy issues: Reduce scope to Doji + Hammer only

## Dependencies & Integration Points

### Sprint Dependencies
- **Prerequisite:** Sprint 4 TickStockApp cleanup completed
- **Concurrent:** Redis setup and configuration
- **Next Sprint:** Sprint 6 requires EventPublisher and PatternScanner foundation

### External Dependencies
- Redis server running and accessible
- Sample OHLCV data for testing (create synthetic if needed)
- Python packages: pandas, redis, pytest

### Integration Handoffs
- **To Sprint 6:** Working EventPublisher, PatternScanner, and core patterns
- **To TickStockApp:** Event structure specification and Redis channel details
- **To Testing:** Unit test framework and integration test patterns

## Future Considerations

### Sprint 6 Preparation
- RealTimeScanner will extend PatternScanner foundation
- Event subscriber integration in TickStockApp will consume events
- Additional patterns will use BasePattern framework

### Extensibility Features
- Composite pattern support (User Story 9) architecture preparation
- ML pattern integration points in BasePattern design
- Multi-symbol scanning optimization hooks

### Performance Optimization Opportunities
- Vectorized operations across multiple patterns
- Caching mechanisms for repeated calculations
- Memory optimization for large datasets

## Sprint Completion Criteria

**Sprint 5 is complete when:**
1. All deliverables are implemented and tested
2. Demo script successfully shows end-to-end pattern detection
3. Performance benchmarks meet <50ms requirement
4. Integration tests pass for EventPublisher → Redis → consumption
5. Documentation updated with implementation details
6. Code review completed and approved
7. Sprint 6 handoff materials prepared

**Milestone Achievement:** End-to-end pattern-to-event flow with mock data working successfully, establishing foundation for real-time scanning in Sprint 6.