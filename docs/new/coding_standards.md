# TickStock Coding Standards

## To Do


## Patterns to Clean Up and Not Support

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

#### Current Cleanup Status

**Files with patterns to clean up:**
1. `src\api\rest\api.py` - Multiple nested patterns checking for `websocket_publisher`
2. `src\core\services\market_data_service.py` - Missing method `get_current_analytics` (BUG)
3. `src\monitoring\health_monitor.py` - Nested check for `trend_detector.last_sent_trends`
4. `src\presentation\websocket\publisher.py` - Nested check for `market_service.get_analytics_for_websocket`

**Action Plan:**
- Fix as encountered during development
- Priority 1: Fix actual bugs (missing methods/attributes)
- Priority 2: Remove unnecessary nested checks where all attributes exist
- Priority 3: Review and document optional vs required components

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

### 3. Direct None Checks vs hasattr

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

## Development Guidelines

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

### Tools Available
- `u_lazy_load_search.py` - Finds all lazy loading patterns
- `u_lazy_load_analyzer.py` - Validates if attributes actually exist and categorizes patterns

## Notes
- This is a living document that will be updated as patterns are cleaned up
- Focus on fixing bugs first, then removing unnecessary defensive code
- Keep legitimate compatibility and optional feature checks