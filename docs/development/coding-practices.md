# TickStock Coding Practices & Standards

**Purpose**: Comprehensive coding standards and best practices for TickStock development  
**Audience**: Development teams, code reviews, quality assurance  
**Last Updated**: 2025-08-21  

## Core Development Philosophy

TickStock follows proven software engineering principles optimized for real-time financial data processing.

### KISS (Keep It Simple, Stupid)
Simplicity should be a key goal in design. Choose straightforward solutions over complex ones whenever possible. Simple solutions are easier to understand, maintain, and debug.

### YAGNI (You Aren't Gonna Need It)
Avoid building functionality on speculation. Implement features only when they are needed, not when you anticipate they might be useful in the future.

### DRY (Don't Repeat Yourself)
Avoid duplication by abstracting common functionality into reusable components.

### Design Principles
- **Dependency Inversion**: High-level modules should not depend on low-level modules. Both should depend on abstractions.
- **Open/Closed Principle**: Software entities should be open for extension but closed for modification.
- **Single Responsibility**: Each function, class, and module should have one clear purpose.
- **Fail Fast**: Check for potential errors early and raise exceptions immediately when issues occur.
- **Technical Waste**: Unnecessary or redundant code, processes, or resources that do not contribute to the system's functionality or value.
- **Technical Debt**: The implied cost of future rework due to choosing a quick, suboptimal solution now instead of a more robust one.

---

## Code Structure & Modularity

### File and Function Limits
- **Avoid creating a file longer than 500 lines of code**. If approaching this limit, refactor by splitting into modules.
- **Functions should be under 50 lines** with a single, clear responsibility.
- **Classes should be under 500 lines** and represent a single concept or entity.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.
- **Line length should be max 100 characters** (ruff rule in pyproject.toml)

---

## Python Style Guide

### Core Principles
- Follow PEP 8 as the foundation with specific adaptations for real-time financial systems
- Consistency is key - maintain patterns across all market data processing modules
- Type safety first - leverage Python's type system for market event clarity and maintainability
- Documentation matters - every service, processor, and event handler needs clear documentation

---

## Naming Conventions

- **Variables and functions**: snake_case (e.g., `process_tick`, `market_data`)
- **Classes**: PascalCase (e.g., `MarketDataService`, `WebSocketManager`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `COLLECTION_INTERVAL`, `MAX_BUFFER_SIZE`)
- **Private attributes/methods**: _leading_underscore (e.g., `_validate_tick`)
- **Type aliases**: PascalCase (e.g., `TickData`, `EventPayload`)
- **Enum values**: UPPER_SNAKE_CASE (e.g., `EventType.HIGH`, `EventType.SURGE`)

### Length Standards
- **Class Length**: When possible, maximum 500 lines (excluding docstring and decorators)
- **Method Length**: When possible, maximum 50 lines (excluding docstring and decorators)

---

## Error Handling Best Practices

### Custom Exception Hierarchy
Create custom exceptions for the market data domain:

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
```

### Exception Handling Patterns
Use specific exception handling in the market pipeline:

```python
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
```

### Context Managers
Use context managers for connection management:

```python
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

---

## Logging Strategy

### Standard Logging
```python
import logging
from functools import wraps

# Configure standard logging
logger = logging.getLogger(__name__)

# Log market event processing
def log_market_event(func):
    @wraps(func)
    def wrapper(self, ticker: str, *args, **kwargs):
        logger.debug(f"Processing {ticker} in {func.__name__}")
        try:
            result = func(self, ticker, *args, **kwargs)
            if result:
                logger.info(f" {func.__name__}: {ticker} - {result.type}")
            return result
        except Exception as e:
            logger.exception(f"L Error in {func.__name__} for {ticker}: {e}")
            raise
    return wrapper

# Sprint-specific logging
logger.info(" SPRINT 29: Pull model enabled with DataPublisher")
logger.info(f"=� Market data pipeline initialized: {len(tickers)} tickers")
```

---

## Configuration Management

### Environment Variables and Settings
Use Pydantic for type-safe configuration management:

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

# Usage
settings = get_market_settings()
data_provider = PolygonDataProvider(settings.polygon_api_key)
```

---

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
```

---

## Search Command Requirements

**CRITICAL**: Use `rg` (ripgrep) instead of traditional `grep` and `find` commands:

```bash
# L Don't use grep
grep -r "pattern" .

#  Use rg instead
rg "pattern"

# L Don't use find with name
find . -name "*.py"

#  Use rg with file filtering
rg --files | rg "\.py$"
# or
rg --files -g "*.py"
```

---

## Code Quality Standards

### Type Safety
- Use type hints for all function parameters and return values
- Leverage Python's type system for market event clarity
- Use Optional[T] for nullable values
- Use Union types sparingly and prefer protocols when possible

### Performance Considerations
- Memory-first processing for sub-millisecond performance
- Database sync every 10 seconds (500:1 write reduction)
- Redis for user preferences and universe caching
- Batch operations where possible

### Security Practices
- Always follow security best practices
- Never introduce code that exposes or logs secrets and keys
- Never commit secrets or keys to the repository
- Use environment variables for sensitive configuration

---

## Code Review Guidelines

### Before Submitting Code
1. Follow all naming conventions and style guidelines
2. Ensure code is under length limits (500 lines/file, 50 lines/function)
3. Add comprehensive docstrings and comments
4. Include appropriate error handling
5. Write tests for new functionality
6. Run linting and type checking

### Review Checklist
- [ ] Code follows TickStock naming conventions
- [ ] Functions and classes are appropriately sized
- [ ] Error handling is comprehensive and follows patterns
- [ ] Logging is appropriate and follows domain patterns
- [ ] Configuration follows Pydantic patterns
- [ ] Type hints are complete and accurate
- [ ] Tests are included for new functionality
- [ ] Documentation is complete and accurate

---

## Anti-Patterns to Avoid

### 1. Overly Defensive Lazy Loading (Nested `hasattr` Checks)

**❌ AVOID: Nested hasattr patterns**
```python
# BAD - Overly defensive nested checks
if hasattr(market_service, 'websocket_publisher') and market_service.websocket_publisher:
    if hasattr(market_service.websocket_publisher, 'user_settings_service') and \
       market_service.websocket_publisher.user_settings_service:
        market_service.websocket_publisher.user_settings_service.app = app
```

**✅ PREFERRED: Direct fail-fast access**
```python
# GOOD - Direct access with fail-fast behavior
market_service.websocket_publisher.user_settings_service.app = app
```

**✅ ACCEPTABLE: Single-level checks for optional components**
```python
# OK - When component is genuinely optional or for backward compatibility
if hasattr(self.market_service, 'event_manager'):  # Optional feature check
    self.market_service.event_manager.reset_all_for_new_session(new_session)
```

#### When to Use `hasattr` Checks

**Legitimate uses (KEEP):**
- Backward compatibility during migration periods
- Optional features/plugins that may not be installed
- Configuration-dependent components
- Cross-version compatibility

**Problematic uses (REMOVE):**
- Nested checks for attributes that should always exist
- Defensive programming hiding initialization bugs
- Multiple chained hasattr checks in compound conditions

### 2. Initialization Order Dependencies

**❌ AVOID: Implicit initialization dependencies**
```python
# BAD - Assumes services are initialized in specific order
class ServiceA:
    def __init__(self):
        self.service_b = None  # Set later by app.py
        
# Later in app.py
service_a.service_b = service_b  # Fragile!
```

**✅ PREFERRED: Explicit dependency injection**
```python
# GOOD - Dependencies passed at construction
class ServiceA:
    def __init__(self, service_b: ServiceB):
        self.service_b = service_b
```

### 3. Inconsistent None vs hasattr Patterns

**❌ AVOID: Mixing patterns inconsistently**
```python
# BAD - Inconsistent checking patterns
if self.real_time_adapter and hasattr(self.real_time_adapter, 'client'):
    if hasattr(self.real_time_adapter.client, 'connected'):
        # ...
```

**✅ PREFERRED: Consistent None checks for objects**
```python
# GOOD - Clear None checks without hasattr for attribute existence
if self.real_time_adapter and self.real_time_adapter.client:
    if self.real_time_adapter.client.connected:
        # ...
```

### 4. Method/Attribute Existence Assumptions

**❌ AVOID: Calling methods that might not exist**
```python
# BAD - Assumes method exists without verification
memory_analytics.get_current_analytics()  # Method doesn't exist!
```

**✅ PREFERRED: Ensure interfaces are well-defined**
```python
# GOOD - Use actual method names or define clear interfaces
memory_analytics.get_analytics_snapshot()  # Actual method name
```

---

## Development and Refactoring Guidelines

### During Development
1. **Fail Fast**: Let AttributeErrors surface during development to catch bugs early
2. **Document Optional Components**: Clearly mark which components are optional vs required
3. **Use Type Hints**: Help IDEs and developers understand expected attributes
4. **Test Initialization**: Ensure all required services are properly initialized

### During Refactoring
1. When encountering nested `hasattr` patterns, evaluate if they're hiding bugs
2. Document why single-level `hasattr` checks exist (backward compatibility, optional features)
3. Replace defensive patterns with proper initialization and dependency injection
4. Add tests to verify all required attributes exist after initialization

### Legacy Code Cleanup
- **Priority 1**: Fix actual bugs (missing methods/attributes)
- **Priority 2**: Remove unnecessary nested checks where all attributes exist
- **Priority 3**: Review and document optional vs required components

---

This guide ensures consistent, maintainable, and high-performance code across all TickStock development while adhering to industry best practices for real-time financial systems.