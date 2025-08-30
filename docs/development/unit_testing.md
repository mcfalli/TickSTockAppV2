# TickStock Unit Testing & Test Organization Guide

**Purpose**: Comprehensive testing standards and organization for TickStock market data system  
**Audience**: Development teams, sprint implementation, quality assurance  
**Last Updated**: 2025-08-21  

## Testing Philosophy

TickStock uses a comprehensive testing strategy with pytest for quality assurance and performance verification of our real-time market data processing system.

### Core Principles
- **Quality First**: No feature is complete without tests
- **Performance Critical**: Sub-millisecond processing requires performance validation
- **Zero Event Loss**: Testing must validate Pull Model architecture integrity
- **Functional Organization**: Tests organized by business domain, not technical structure

---

## Test Organization & Structure

Tests are organized by functional area for easy navigation and sprint-specific work:

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── fixtures/                     # Shared test data and utilities
│
├── event_processing/             # Event Processing & Detection
│   ├── sprint_107/              # Sprint-specific event processing refactor
│   │   ├── test_event_processor_refactor.py
│   │   ├── test_multi_source_integration.py
│   │   └── test_existing_functionality_preservation.py
│   ├── detectors/               # Event detector tests
│   │   ├── test_highlow_detector.py
│   │   ├── test_trend_detector.py
│   │   └── test_surge_detector.py
│   └── events/                  # Event model tests
│       ├── test_base_events.py
│       ├── test_event_creation.py
│       └── test_event_serialization.py
│
├── data_processing/              # Data Processing & Channels
│   ├── sprint_105/              # Core channel infrastructure
│   │   ├── test_base_channel.py
│   │   ├── test_channel_router.py
│   │   └── test_channel_metrics.py
│   ├── sprint_106/              # Data type handlers
│   │   ├── test_data_types.py
│   │   ├── test_tick_channel.py
│   │   └── test_multi_channel_integration.py
│   └── providers/               # Data provider tests
│       ├── test_polygon_provider.py
│       └── test_synthetic_provider.py
│
├── websocket_communication/      # WebSocket & Real-time Communication
│   ├── publishers/              # WebSocket publisher tests
│   ├── clients/                 # WebSocket client tests
│   └── protocols/               # Communication protocol tests
│
├── market_data/                  # Market Data Processing
│   ├── services/                # Market data service tests
│   ├── aggregation/             # Data aggregation tests
│   └── analytics/               # Market analytics tests
│
├── infrastructure/               # Infrastructure & External Systems
│   ├── database/                # Database integration tests
│   ├── caching/                 # Redis/caching tests
│   └── external_apis/           # External API integration tests
│
├── user_management/              # User & Authentication
│   ├── authentication/          # Auth tests
│   ├── preferences/             # User preference tests
│   └── sessions/                # Session management tests
│
└── system_integration/           # End-to-End System Tests
    ├── performance/             # System performance tests
    ├── regression/              # System regression tests
    └── end_to_end/             # Complete workflow tests
```

### Test Organization Guidelines
- **Functional Area First**: Tests grouped by primary functionality
- **Sprint Subfolders**: Sprint-specific work gets its own subfolder within functional area
- **Component Subfolders**: Related components grouped together
- **Clear Navigation**: Easy to find all tests related to a specific feature
- **Separation of Concerns**: System tests separate from component tests

### Test Types and Markers
- `@pytest.mark.unit` - Fast, isolated component tests
- `@pytest.mark.integration` - Multi-component interaction tests  
- `@pytest.mark.performance` - Performance and load tests
- `@pytest.mark.slow` - Tests that take > 1 second
- `@pytest.mark.api` - Tests requiring external API calls
- `@pytest.mark.database` - Tests requiring database access

---

## Functional Area Selection

Choose the appropriate functional area for your Sprint:

| **Functional Area** | **Use For** | **Examples** |
|-------------------|-------------|-------------|
| `event_processing/` | Event processing, detection, event models | EventProcessor, detectors, event creation |
| `data_processing/` | Data channels, providers, data types | Channels, routers, OHLCV/FMV data |
| `websocket_communication/` | WebSocket publishers, clients, protocols | WebSocket publisher, real-time communication |
| `market_data/` | Market data services, aggregation, analytics | MarketDataService, analytics, aggregation |
| `infrastructure/` | Database, caching, external APIs | Database integration, Redis, Polygon API |
| `user_management/` | Authentication, preferences, sessions | User auth, preferences, session management |
| `system_integration/` | End-to-end, performance, regression | System-wide tests, performance benchmarks |

---

## Test Configuration (pytest.ini)

- **Coverage Target**: 70% minimum for core business logic
- **Test Markers**: unit, integration, performance, slow, api, database
- **Coverage Reports**: HTML (htmlcov/) + terminal output
- **Test Discovery**: Automatic for test_*.py files

---

## Quick Test Commands

### Development Cycle Commands
```bash
# Fast development cycle
make test-quick              # Run fast tests only
make test-unit              # Unit tests with coverage
make test-all               # Full test suite
```

### Functional Area Testing (Recommended)
```bash
pytest tests/event_processing/ -v           # All event processing tests
pytest tests/data_processing/ -v            # All data processing tests
pytest tests/websocket_communication/ -v    # All WebSocket tests
pytest tests/market_data/ -v                # All market data tests
```

### Sprint-Specific Testing
```bash
pytest tests/event_processing/sprint_107/ -v    # Sprint 107 event processing
pytest tests/data_processing/sprint_105/ -v     # Sprint 105 channels
pytest tests/data_processing/sprint_106/ -v     # Sprint 106 data types
pytest tests/system_integration/sprint_108/ -v  # Sprint 108 integration
```

### Component-Specific Testing
```bash
pytest tests/event_processing/detectors/ -v     # All detector tests
pytest tests/event_processing/events/ -v        # All event model tests
pytest tests/data_processing/providers/ -v      # All data provider tests
```

### System-Level Testing
```bash
pytest tests/system_integration/ -v             # All system integration tests
pytest tests/system_integration/performance/ -v # Performance tests only
pytest tests/system_integration/regression/ -v  # Regression tests only
```

### Legacy Commands (Still Functional)
```bash
# Quick feedback loop (recommended for active development)
python -m pytest tests/unit/processing/ -v -x --tb=short

# Test specific functionality
python -m pytest tests/unit/processing/test_highlow_detector.py::TestHighLowDetectorBasicDetection -v

# Performance testing for real-time components
python -m pytest tests/ -v -m performance

# Run tests and generate HTML coverage report
python -m pytest tests/unit/ --cov=src --cov-report=html
# Open htmlcov/index.html to view detailed coverage
```

### Continuous Integration
```bash
# Full test suite (what CI runs)
python -m pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=70

# Quality checks
ruff check src/ tests/
mypy src/ --ignore-missing-imports
```

### Test Filtering
```bash
# Fast tests only (skip slow, API, database tests)
python -m pytest tests/ -m "not slow and not api and not database"

# Unit tests for specific component
python -m pytest tests/unit/core/ -v

# All integration tests
python -m pytest tests/integration/ -v

# Performance benchmarks only
python -m pytest tests/ -m performance --tb=short
```

---

## Required Test Coverage for Sprints

Create comprehensive test suites with the following structure:

### Test File Requirements

#### 1. Unit/Refactor Tests: `test_<component>_refactor.py`
- Test individual component functionality
- Test new methods and interfaces  
- Test initialization and configuration
- **Target**: 30+ test methods

#### 2. Integration Tests: `test_<feature>_integration.py`
- Test end-to-end feature workflows
- Test component interactions
- Test external system integrations
- **Target**: 15+ test methods

#### 3. Regression Tests: `test_<feature>_preservation.py`
- Test backward compatibility preservation
- Test existing functionality unchanged
- Test performance has not regressed
- **Target**: 20+ test methods

#### 4. Performance Tests: `test_<component>_performance.py` (if applicable)
- Test processing speed requirements
- Test memory usage patterns
- Test scalability characteristics
- **Target**: 5+ test methods

### Test Quality Standards
- **Coverage**: Comprehensive coverage of new functionality
- **Compatibility**: Verify all existing functionality preserved
- **Performance**: Validate performance meets existing benchmarks
- **Error Handling**: Test error scenarios and edge cases
- **Documentation**: All test classes and complex methods documented

---

## Writing Tests - Key Patterns

### 1. Test Structure (Arrange-Act-Assert)
```python
def test_high_low_event_creation(event_builder):
    # Arrange - Set up test data
    ticker = "AAPL"
    price = 150.25
    
    # Act - Execute the functionality
    event = event_builder.high_low_event(ticker=ticker, price=price)
    
    # Assert - Verify the results
    assert event.ticker == ticker
    assert event.price == price
    assert event.type == "high"
```

### 2. Use Fixtures for Test Data
```python
@pytest.fixture
def mock_tick():
    return MockTick.create(ticker="AAPL", price=150.0, volume=1000)

def test_event_detection(mock_tick, detector):
    result = detector.detect(mock_tick.ticker, mock_tick.price)
    assert result is not None
```

### 3. Performance Testing
```python
@pytest.mark.performance
def test_detection_performance(detector, performance_timer):
    """Ensure sub-millisecond detection performance"""
    iterations = 1000
    
    performance_timer.start()
    for i in range(iterations):
        # Test with varying price data
        tick_data = create_test_tick(price=150.0 + i*0.001)
        detector.detect_highlow(tick_data, stock_data)
    performance_timer.stop()
    
    avg_time = performance_timer.elapsed / iterations
    assert avg_time < 0.001  # Less than 1ms per detection
```

### 4. Mock External Dependencies
```python
@patch('requests.get')
def test_polygon_api_integration(mock_get, provider):
    """Test API integration with mocked responses"""
    mock_get.return_value.json.return_value = {"status": "OK", "results": [...]}
    
    result = provider.get_tick("AAPL")
    
    mock_get.assert_called_once()
    assert result is not None
```

---

## Testing Requirements by Component

### Core Domain Events (src/core/domain/events/)
- ✅ Event creation and validation
- ✅ Transport dict generation
- ✅ Event ID uniqueness
- ✅ Performance benchmarks

### Event Detectors (src/processing/detectors/)
- ✅ Detection logic accuracy
- ✅ Threshold configuration
- ✅ Edge case handling
- ✅ Performance under load

### Data Providers (src/infrastructure/data_sources/)
- ✅ API response handling
- ✅ Error recovery
- ✅ Fallback mechanisms
- ✅ Rate limiting compliance

### WebSocket Components (src/presentation/websocket/)
- 🔄 Event emission
- 🔄 User filtering
- 🔄 Connection management
- 🔄 Message serialization

---

## Test Execution Performance Requirements

- **Unit Tests**: < 10 seconds total execution
- **Integration Tests**: < 30 seconds total execution
- **Individual Test**: < 100ms maximum
- **Memory Usage**: No memory leaks during test runs

---

## Continuous Integration

- **GitHub Actions**: Automated on push/PR
- **Multi-Python**: Tests on 3.9, 3.10, 3.11
- **Quality Gates**: Linting, type checking, security scan
- **Coverage Reporting**: Codecov integration

---

## Test Data Management

- **Fixtures**: Reusable test data in conftest.py
- **Builders**: EventBuilder for creating test events
- **Generators**: MarketDataGenerator for realistic data
- **Mocks**: Database, Redis, WebSocket, API responses

---

## Development Workflow

1. **Write failing test** for new feature
2. **Implement minimum code** to pass test
3. **Refactor** while keeping tests green
4. **Run full test suite** before committing
5. **Check coverage** meets minimum threshold

---

## Test Debugging

```bash
# Run single test with detailed output
pytest tests/unit/core/test_events.py::TestHighLowEvent::test_create_valid_high_event -v -s

# Profile slow tests
pytest tests/ --durations=10

# Debug test failures
pytest tests/ --pdb --tb=short
```

---

## Testing DON'Ts and DOs

### DON'T
- **Skip writing tests** for new functionality
- **Mock everything** - test real domain logic
- Mix typed events and dicts after Worker boundary
- Push events directly (always use Pull Model)
- Create synchronous WebSocket operations
- Access database in hot paths (use memory/cache)

### DO
- **Write tests first** for complex logic
- **Use appropriate test types** (unit vs integration)
- **Mock external dependencies** only
- Maintain event type consistency through pipeline
- Let WebSocketPublisher control emission timing
- Use Redis/memory for real-time operations
- Test error scenarios and edge cases

---

## Sprint Testing Workflow

### During Sprint Development:
1. Create test files in appropriate functional area and sprint subfolder
2. Follow the required test coverage structure (refactor, integration, preservation, performance)
3. Run tests continuously during development
4. Maintain performance benchmarks established in Sprint 108

### Sprint Completion Testing:
1. Execute complete functional area test suite
2. Run performance validation tests
3. Verify no regression in existing functionality
4. Update test documentation and coverage reports

---

## Configuration Best Practices
- Use **numeric values** for thresholds (not strings): `0.01` not `"0.01"`
- **Mock external services** (APIs, databases) in unit tests
- **Realistic test data** that mirrors production scenarios
- **Environment isolation** - tests shouldn't affect each other

---

## Current Test Results & Framework Status

### Coverage Status (Sprint 108 Baseline)
- **HighLowDetector**: 70% coverage (core business logic)
- **Event Classes**: 84% coverage  
- **Test Infrastructure**: 100% operational
- **Multi-Channel System**: Comprehensive integration test coverage

### Performance Benchmarks Met ✅
- **Individual tests**: < 100ms execution (requirement met)
- **Detection performance**: Sub-millisecond processing validated
- **Memory stability**: No leaks during sustained processing
- **System integration**: 8,000+ OHLCV symbols validated
- **Latency requirements**: <50ms P99 tick processing confirmed

### Quality Gates ✅
- **Comprehensive test coverage** across functional areas
- **Sprint-specific regression testing** implemented
- **Performance validation** integrated into CI pipeline
- **Error handling** and edge case coverage

---

## Troubleshooting Common Issues

### Configuration Errors
```python
# ❌ Wrong: String values cause multiplication errors
config = {'HIGHLOW_MIN_PRICE_CHANGE': '0.01'}

# ✅ Correct: Use numeric values
config = {'HIGHLOW_MIN_PRICE_CHANGE': 0.01}
```

### Mock vs Real Data
```python
# ❌ Wrong: Testing with unrealistic data
tick_data = TickData("TEST", price=0, volume=1000)  # Invalid price

# ✅ Correct: Use realistic market data
tick_data = TickData("AAPL", price=150.25, volume=1000)
```

### Performance Expectations
```python
# ❌ Wrong: Unrealistic performance expectations
assert avg_time < 0.0001  # 0.1ms too aggressive for complex detection

# ✅ Correct: Realistic real-time performance requirements
assert avg_time < 0.001   # 1ms is excellent for financial processing
```

---

## Framework Integration

### Key Files Reference
- `tests/conftest.py` - Shared fixtures and test configuration
- `tests/fixtures/` - Reusable test data and utilities  
- `pytest.ini` - Test runner configuration with coverage and markers
- `requirements/dev.txt` - Testing dependencies

### Integration Points
- **CLAUDE.md**: References this guide for sprint testing standards
- **CI/CD Pipeline**: Automated test execution and quality gates
- **Sprint Documentation**: Performance baselines and testing requirements
- **Development Workflow**: TDD practices and coverage requirements

This guide ensures consistent, comprehensive testing across all TickStock development while maintaining our critical performance and reliability requirements for real-time market data processing.