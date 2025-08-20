# CLAUDE.md

This file provides comprehensive guidance to Claude Code when working with Python code in this repository.
**Important** - CLAUDE documentation is stored local at ./claude-code-docs to reference not having to go out to anthropic to find documentation.  This is kept current daily. 


## Important Notes
- **NEVER ASSUME OR GUESS** - When in doubt, ask for clarification
- **Always verify file paths and module names** before use
- **Keep CLAUDE.md updated** when adding new patterns or dependencies
- **Test your code** - No feature is complete without tests (see Testing Framework section)
- **Document your decisions** - Future developers (including yourself) will thank you
_This document is a living guide. Update it as the project evolves and new patterns emerge._

## What is TickStock?
TickStock is a high-performance, real-time market data processing system that handles 4,000+ stock tickers with sub-millisecond event detection. It processes WebSocket data streams from Polygon.io (production) or synthetic data (development) and delivers personalized, filtered market events to users via WebSocket connections.

## Core Value Proposition
- Real-time processing of market data with <100ms end-to-end latency
- Zero event loss through Pull Model architecture
- Per-user filtering

# Technology Stack
Backend: Python 3.x, Flask, Flask-SocketIO, Eventlet
Frontend: JavaScript ES6+ SPA with Socket.IO client
Database: PostgreSQL with SQLAlchemy
Cache: Redis for user preferences and universe caching
Data Provider: Polygon.io (live) / Synthetic (dev/test)
Architecture: Component-based with Pull Model Event Distribution

## Critical Architecture Patterns
### Pull Model (Sprint 29) - MUST MAINTAIN
- DataPublisher collects and buffers events (no emission)
- WebSocketPublisher pulls when ready (controls flow)
- Zero event loss guaranteed
- Buffer overflow protection (1000 events/type max)
### Event Type Boundary
- Detection → Worker: Typed Events (HighLowEvent, TrendEvent, SurgeEvent)
- Worker → Display Queue: Dict conversion via `to_transport_dict()`
- Display Queue → Frontend: Dict only
- **Never mix typed events and dicts after Worker conversion**
### Memory-First Processing
- All operations in memory for sub-millisecond performance
- Database sync every 10 seconds (500:1 write reduction)
- Redis for user preferences and universe caching


## Key Components Reference
### Core Processing Pipeline
1. **app.py** → Flask application entry point
2. **core_service.py** → WebSocket tick handler & orchestrator
3. **event_processor.py** → Main event processing logic
4. **event_detector.py** → High/Low, Trend, Surge detection
5. **data_publisher.py** → Event collection & buffering
6. **websocket_publisher.py** → Pull-based emission to users
### Database Models
- **cache_entries** → Core universe definitions
- **user_universe** → Per-user stock selections
- **analytics_data** → Stored analytics results
- **app_readwrite** → Database user for application


# Sprint Management
Sprint Capacity Monitoring: Alert at 80% chat capacity
Context Preservation: Capture all relevant context before chat transitions
Task Tracking: Maintain sprint tasks with ongoing task list for items that arise


# Git Workflow
Branch Strategy
main - primary repository 
**NEVER include claude code, written by claude code, or any Generated with Claude Code attribution in commit messages**
Do NOT add these lines to any commits:
- 🤖 Generated with [Claude Code](https://claude.ai/code)  
- Co-Authored-By: Claude <noreply@anthropic.com>
``
<type>(<scope>): <subject>
<body>
<footer>
``
``
Types: feat, fix, docs, style, refactor, test, chore
Example:
feat(auth): add two-factor authentication
Implement TOTP generation and validation
Add QR code generation for authenticator apps
Update user model with 2FA fields
Closes #123
``

# AI Dev Tasks
Use these files when I request structured feature development using PRD or Sprint:
tasks\templates\create-prd.md
tasks\templates\generate-tasks.md
tasks\templates\process-task-list.md

# Communication Protocol
When working on sprints/problems:
Repeat understanding of goals in response
Analyze and summarize the approach
Ask clarifying questions before generating code
Provide clear directions with code examples
Track additional items that arise during sprint work

## Core Development Philosophy
### KISS (Keep It Simple, Stupid)
Simplicity should be a key goal in design. Choose straightforward solutions over complex ones whenever possible. Simple solutions are easier to understand, maintain, and debug.
### YAGNI (You Aren't Gonna Need It)
Avoid building functionality on speculation. Implement features only when they are needed, not when you anticipate they might be useful in the future.
### DRY (Don’t Repeat Yourself) 
Avoid duplication by abstracting common functionality into reusable components.

### Design Principles
- **Dependency Inversion**: High-level modules should not depend on low-level modules. Both should depend on abstractions.
- **Open/Closed Principle**: Software entities should be open for extension but closed for modification.
- **Single Responsibility**: Each function, class, and module should have one clear purpose.
- **Fail Fast**: Check for potential errors early and raise exceptions immediately when issues occur.
- **Technical Waste**: Unnecessary or redundant code, processes, or resources that do not contribute to the system's functionality or value.
- **Technical Debt**: The implied cost of future rework due to choosing a quick, suboptimal solution now instead of a more robust one.

## Project Structure
.\docs\new\project_structure.md
.\docs\new\project_structure_docs.md

## Project Structure Folders, Code Files, Class Names, Method Names, Return Values, References


## Code Structure & Modularity
### File and Function Limits
- **Avoid creating a file longer than 500 lines of code**. If approaching this limit, refactor by splitting into modules.
- **Functions should be under 50 lines** with a single, clear responsibility.
- **Classes should be under 500 lines** and represent a single concept or entity.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
- **Line length should be max 100 characters** ruff rule in pyproject.toml


## Style & Conventions
### Python Style Guide
- Core Principles**
- Follow PEP 8 as the foundation with specific adaptations for real-time financial systems
- Consistency is key - maintain patterns across all market data processing modules
- Type safety first - leverage Python's type system for market event clarity and maintainability
- Documentation matters - every service, processor, and event handler needs clear documentation


## Common Development Tasks
### Adding a New Event Type
1. Create typed event class in `src/shared/models/events/`
2. Add detection logic in appropriate detector
3. Implement `to_transport_dict()` method
4. Update PriorityManager for routing
5. Add frontend handler for new event type
### Modifying Database Schema
```sql
-- Always provide both ALTER and CREATE statements
ALTER TABLE table_name ADD COLUMN new_column TYPE;
GRANT SELECT, INSERT, UPDATE, DELETE ON table_name TO app_readwrite;



## Code Documentation
- if you create or update documentation in docs folder, update the date and time at the top of file and add a line for sprint # and description if applicable
- Every module should have a docstring explaining its purpose
- Public functions must have complete docstrings
- Complex logic should have inline comments with `# Reason:` prefix
- Keep folder level README.md files updated with setup instructions and examples

## Docstring Standards
***Use Google-style docstrings for all public functions, classes, and modules:***
```python
pythondef detect_surge_event(
    ticker: str,
    current_volume: float,
    avg_volume: float,
    threshold_multiplier: float = 3.0
) -> Optional[SurgeEvent]:
    """
    Detect volume surge events in market data.

    Args:
        ticker: Stock ticker symbol
        current_volume: Current period volume
        avg_volume: Average volume for comparison period
        threshold_multiplier: Surge detection threshold (default 3x)

    Returns:
        SurgeEvent if surge detected, None otherwise

    Raises:
        ValueError: If volumes are negative or threshold < 1.0
        DataProviderError: If market data unavailable

    Example:
        >>> surge = detect_surge_event("AAPL", 5000000, 1000000)
        >>> if surge:
        ...     websocket_manager.broadcast_event(surge)
    """
```
## Naming Conventions
Variables and functions: snake_case (e.g., process_tick, market_data)
Classes: PascalCase (e.g., MarketDataService, WebSocketManager)
Constants: UPPER_SNAKE_CASE (e.g., COLLECTION_INTERVAL, MAX_BUFFER_SIZE)
Private attributes/methods: _leading_underscore (e.g., _validate_tick)
Type aliases: PascalCase (e.g., TickData, EventPayload)
Enum values: UPPER_SNAKE_CASE (e.g., EventType.HIGH, EventType.SURGE)
Class Length Standards: When possible Maximum: 500 lines (excluding docstring and decorators)
Method Length Standards: When possible Maximum: 50 lines (excluding docstring and decorators)

## 🚨 Error Handling
Exception Best Practices
python# Create custom exceptions for market data domain
```python
class MarketDataError(Exception):
    """Base exception for market data processing errors."""
    pass

class DataProviderError(MarketDataError):
    """Raised when data provider (Polygon/Simulated) fails."""
    def __init__(self, provider: str, reason: str):
        self.provider = provider
        self.reason = reason
        super().__init__(
            f"Data provider {provider} failed: {reason}"
        )

class EventDetectionError(MarketDataError):
    """Raised when event detection logic fails."""
    pass

class WebSocketError(MarketDataError):
    """Raised for WebSocket communication failures."""
    pass

# Use specific exception handling in market pipeline
try:
    tick_data = await data_provider.get_tick(ticker)
    event = event_processor.process_tick(tick_data)
    websocket_manager.broadcast_event(event)
except DataProviderError as e:
    logger.warning(f"Falling back to simulated data: {e}")
    tick_data = simulated_provider.generate_tick(ticker)
except EventDetectionError as e:
    logger.error(f"Event detection failed for {ticker}: {e}")
    tracer.add_trace("event_detection_error", ticker, error=str(e))
except WebSocketError as e:
    logger.error(f"WebSocket broadcast failed: {e}")
    # Queue for retry with exponential backoff

# Use context managers for connection management
from contextlib import contextmanager

@contextmanager
def websocket_connection(client_id: str):
    """Provide managed WebSocket connection scope."""
    ws = WebSocketConnection(client_id)
    try:
        ws.connect()
        yield ws
        ws.send_heartbeat()
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        raise
    finally:
        ws.disconnect()
```

## Logging Strategy
```python
from config.logging_config import get_domain_logger, LogDomain
from functools import wraps
# Configure domain-specific logging
logger = get_domain_logger(LogDomain.CORE, "market_service")

# Log market event processing
def log_market_event(func):
    @wraps(func)
    def wrapper(self, ticker: str, *args, **kwargs):
        logger.debug(f"Processing {ticker} in {func.__name__}")
        try:
            result = func(self, ticker, *args, **kwargs)
            if result:
                logger.info(f"✅ {func.__name__}: {ticker} - {result.type}")
            return result
        except Exception as e:
            logger.exception(f"❌ Error in {func.__name__} for {ticker}: {e}")
            raise
    return wrapper

# Sprint-specific logging
logger.info("✅ SPRINT 29: Pull model enabled with DataPublisher")
logger.info(f"📊 Market data pipeline initialized: {len(tickers)} tickers")
```

## 🔧 Configuration Management
***Environment Variables and Settings***
```python
from pydantic import BaseSettings, Field, validator
from functools import lru_cache
from typing import List, Optional

class MarketServiceSettings(BaseSettings):
    """TickStock market service configuration."""
    
    # API Configuration
    polygon_api_key: str = Field(..., env="POLYGON_API_KEY")
    use_simulated_data: bool = Field(False, env="USE_SIMULATED_DATA")
    
    # WebSocket Configuration
    websocket_port: int = Field(5000, env="WEBSOCKET_PORT")
    heartbeat_interval: float = Field(2.0, env="HEARTBEAT_INTERVAL")
    max_connections: int = Field(100, ge=1, le=1000)
    
    # Event Detection
    surge_multiplier: float = Field(3.0, env="SURGE_MULTIPLIER")
    high_low_threshold: float = Field(0.1, env="HIGH_LOW_THRESHOLD")
    trend_windows: List[int] = Field([180, 360, 600], env="TREND_WINDOWS")
    
    # Sprint 29 Pull Model
    collection_interval: float = Field(0.5, env="COLLECTION_INTERVAL")
    emission_interval: float = Field(1.0, env="EMISSION_INTERVAL")
    max_buffer_size: int = Field(1000, env="MAX_BUFFER_SIZE")
    
    # Performance
    worker_pool_size: int = Field(4, env="WORKER_POOL_SIZE")
    enable_tracing: bool = Field(False, env="ENABLE_TRACING")
    
    @validator('surge_multiplier')
    def validate_surge_multiplier(cls, v):
        if v < 1.5 or v > 10.0:
            raise ValueError('Surge multiplier must be between 1.5 and 10.0')
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_market_settings() -> MarketServiceSettings:
    """Get cached market service settings."""
    return MarketServiceSettings()

    #Usage
    settings = get_market_settings()
    data_provider = PolygonDataProvider(settings.polygon_api_key)
```



## Search Command Requirements
**CRITICAL**: Use `rg` (ripgrep) instead of traditional `grep` and `find` commands:
```bash
# ❌ Don't use grep
grep -r "pattern" .
# ✅ Use rg instead
rg "pattern"
# ❌ Don't use find with name
find . -name "*.py"
# ✅ Use rg with file filtering
rg --files | rg "\.py$"
# or
rg --files -g "*.py"
```

## Testing Framework
***TickStock uses a comprehensive testing strategy with pytest for quality assurance and performance verification.***

### Test Organization & Structure
**Organized by Functional Area for Easy Navigation**

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

**Test Organization Guidelines:**
- **Functional Area First**: Tests grouped by primary functionality (event_processing, data_processing, etc.)
- **Sprint Subfolders**: Sprint-specific work gets its own subfolder within the functional area
- **Component Subfolders**: Related components grouped together (detectors, events, providers)
- **Clear Navigation**: Easy to find all tests related to a specific feature
- **Separation of Concerns**: System tests separate from component tests

### Test Configuration (pytest.ini)
- **Coverage Target**: 70% minimum for core business logic
- **Test Markers**: unit, integration, performance, slow, api, database
- **Coverage Reports**: HTML (htmlcov/) + terminal output
- **Test Discovery**: Automatic for test_*.py files

### Quick Test Commands
```bash
# Fast development cycle
make test-quick              # Run fast tests only
make test-unit              # Unit tests with coverage
make test-all               # Full test suite

# Functional area testing (recommended)
pytest tests/event_processing/ -v           # All event processing tests
pytest tests/data_processing/ -v            # All data processing tests
pytest tests/websocket_communication/ -v    # All WebSocket tests
pytest tests/market_data/ -v                # All market data tests

# Sprint-specific testing
pytest tests/event_processing/sprint_107/ -v    # Sprint 107 event processing
pytest tests/data_processing/sprint_105/ -v     # Sprint 105 channels
pytest tests/data_processing/sprint_106/ -v     # Sprint 106 data types

# Component-specific testing
pytest tests/event_processing/detectors/ -v     # All detector tests
pytest tests/event_processing/events/ -v        # All event model tests
pytest tests/data_processing/providers/ -v      # All data provider tests

# System-level testing
pytest tests/system_integration/ -v             # All system integration tests
pytest tests/system_integration/performance/ -v # Performance tests only
pytest tests/system_integration/regression/ -v  # Regression tests only

# Legacy test structure (being migrated)
pytest tests/pipeline/ -v                       # Current Sprint 105-107 tests
pytest tests/unit/ -v                          # Legacy unit tests
```

### Writing Tests - Key Patterns

#### 1. Test Structure (Arrange-Act-Assert)
```python
def test_high_low_event_creation(event_builder):
    # Arrange
    ticker = "AAPL"
    price = 150.25
    
    # Act
    event = event_builder.high_low_event(ticker=ticker, price=price)
    
    # Assert
    assert event.ticker == ticker
    assert event.price == price
    assert event.type == "high"
```

#### 2. Use Fixtures for Test Data
```python
@pytest.fixture
def mock_tick():
    return MockTick.create(ticker="AAPL", price=150.0, volume=1000)

def test_event_detection(mock_tick, detector):
    result = detector.detect(mock_tick.ticker, mock_tick.price)
    assert result is not None
```

#### 3. Performance Testing
```python
@pytest.mark.performance
def test_event_creation_speed(performance_timer):
    performance_timer.start()
    for _ in range(1000):
        create_event()
    performance_timer.stop()
    
    assert performance_timer.elapsed < 0.1  # 100ms max
```

#### 4. Mock External Dependencies
```python
@patch('requests.get')
def test_polygon_api_call(mock_get, provider):
    mock_get.return_value.json.return_value = {"status": "OK"}
    result = provider.get_tick("AAPL")
    assert result is not None
```

### Testing Requirements by Component

#### Core Domain Events (src/core/domain/events/)
- ✅ Event creation and validation
- ✅ Transport dict generation
- ✅ Event ID uniqueness
- ✅ Performance benchmarks

#### Event Detectors (src/processing/detectors/)
- ✅ Detection logic accuracy
- ✅ Threshold configuration
- ✅ Edge case handling
- ✅ Performance under load

#### Data Providers (src/infrastructure/data_sources/)
- ✅ API response handling
- ✅ Error recovery
- ✅ Fallback mechanisms
- ✅ Rate limiting compliance

#### WebSocket Components (src/presentation/websocket/)
- 🔄 Event emission
- 🔄 User filtering
- 🔄 Connection management
- 🔄 Message serialization

### Test Execution Performance Requirements
- **Unit Tests**: < 10 seconds total execution
- **Integration Tests**: < 30 seconds total execution
- **Individual Test**: < 100ms maximum
- **Memory Usage**: No memory leaks during test runs

### Continuous Integration
- **GitHub Actions**: Automated on push/PR
- **Multi-Python**: Tests on 3.9, 3.10, 3.11
- **Quality Gates**: Linting, type checking, security scan
- **Coverage Reporting**: Codecov integration

### Test Data Management
- **Fixtures**: Reusable test data in conftest.py
- **Builders**: EventBuilder for creating test events
- **Generators**: MarketDataGenerator for realistic data
- **Mocks**: Database, Redis, WebSocket, API responses

### Development Workflow
1. **Write failing test** for new feature
2. **Implement minimum code** to pass test
3. **Refactor** while keeping tests green
4. **Run full test suite** before committing
5. **Check coverage** meets minimum threshold

### Test Debugging
```bash
# Run single test with detailed output
pytest tests/unit/core/test_events.py::TestHighLowEvent::test_create_valid_high_event -v -s

# Profile slow tests
pytest tests/ --durations=10

# Debug test failures
pytest tests/ --pdb --tb=short
```

## Common Pitfalls to Avoid
### DON'T
- Mix typed events and dicts after Worker boundary
- Push events directly (always use Pull Model)
- Access database in hot paths (use memory/cache)
- Create synchronous WebSocket operations
- Exceed 500 lines per file or 50 lines per function
- **Skip writing tests** for new functionality
- **Mock everything** - test real domain logic
### DO
- Maintain event type consistency through pipeline
- Let WebSocketPublisher control emission timing
- Use Redis/memory for real-time operations
- Batch DOM updates with requestAnimationFrame
- Refactor when approaching size limits
- **Write tests first** for complex logic
- **Use appropriate test types** (unit vs integration)
- **Mock external dependencies** only