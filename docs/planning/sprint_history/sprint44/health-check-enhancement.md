name: "Health Check Enhancement - Add Redis Status"
description: |

---

## Goal

**Feature Goal**: Enhance the `/health` endpoint to include Redis connectivity status for proactive system monitoring

**Deliverable**: Updated `/health` endpoint returning comprehensive health status including Redis connection state

**Success Definition**:
- `/health` endpoint returns JSON with status, version, AND Redis connectivity status
- Response time < 50ms (non-blocking)
- Integration tests pass
- Manual curl test shows Redis status

## User Persona (if applicable)

**Target User**: DevOps engineers, system administrators, monitoring systems

**Use Case**: Automated health monitoring for load balancers, Kubernetes probes, uptime monitoring services

**User Journey**:
1. Monitoring system makes GET request to `/health`
2. Receives JSON response with overall status + component health
3. Alerts trigger if Redis shows as unhealthy
4. System administrators investigate Redis connectivity issues

**Pain Points Addressed**:
- Currently `/health` only shows "healthy" + version, no component details
- Redis failures aren't detected by simple health check
- Monitoring systems can't differentiate between app vs Redis issues

## Why

- **Proactive monitoring**: Detect Redis connectivity issues before they impact users
- **Debugging efficiency**: Quickly identify if issue is app code vs Redis infrastructure
- **Integration readiness**: Prepare for Kubernetes/Docker health checks that need component status
- **Existing infrastructure**: HealthMonitor service already checks Redis - just expose it via `/health`

## What

Enhance the simple `/health` endpoint at `src/app.py:526` to return:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "redis": {
      "status": "healthy",
      "response_time_ms": 8.5,
      "message": null
    }
  },
  "timestamp": 1642234567.89
}
```

### Success Criteria

- [ ] `/health` endpoint response includes Redis status
- [ ] Response time remains < 50ms (cached, non-blocking)
- [ ] Existing HealthMonitor service reused (no duplication)
- [ ] HTTP status code 200 if Redis healthy, 503 if Redis down
- [ ] Integration test validates new response structure
- [ ] Manual curl test confirms functionality

## All Needed Context

### Context Completeness Check

✅ **Passes "No Prior Knowledge" test**: All file paths, patterns, and gotchas documented below

### TickStock Architecture Context

```yaml
tickstock_architecture:
  component: TickStockAppV2
  role: Consumer

  redis_channels:
    # This feature doesn't subscribe to channels, just checks connectivity
    - channel: "N/A"
      purpose: "Health check only tests connectivity, no subscriptions"
      message_format: "N/A"

  database_access:
    mode: read-only
    tables: []
    queries: "None - health check only"

  websocket_integration:
    broadcast_to: "N/A"
    message_format: "N/A"
    latency_target: "N/A"

  tickstockpl_api:
    endpoints: []
    format: "N/A"

  performance_targets:
    - metric: "Health check response"
      target: "<50ms total response time"

    - metric: "Redis ping"
      target: "<10ms (via HealthMonitor service)"
```

### Documentation & References

```yaml
# External best practices
- url: https://py-healthcheck.readthedocs.io/en/stable/flask.html
  why: "Flask health check library patterns"
  critical: "Cache health check results to avoid hammering Redis (27s success, 9s failure)"

- url: https://medium.com/@encodedots/python-health-check-endpoint-example-a-comprehensive-guide-4d5b92018425
  why: "Best practices for Python health endpoints"
  critical: "Return appropriate HTTP status codes (200=healthy, 503=unhealthy)"

# TickStock-Specific References
- file: src/app.py
  why: "Current health endpoint implementation"
  pattern: "Simple @app.route('/health') returning dict"
  gotcha: "Uses @login_required decorator - health checks should be UNAUTHENTICATED"
  line: 526

- file: src/core/services/health_monitor.py
  why: "Existing Redis health check service"
  pattern: "HealthMonitor._check_redis_health() returns HealthStatus dataclass"
  gotcha: "Already does ping + operations test + performance check"
  line: 116-179

- file: src/config/redis_config.py
  why: "Redis client initialization pattern"
  pattern: "get_redis_client() returns configured redis.Redis instance"
  gotcha: "Returns client but doesn't handle connection failures"
  line: 11-34

- file: tests/core/services/test_health_monitor_refactor.py
  why: "Test patterns for health checking"
  pattern: "Mock Redis client, assert on HealthStatus fields"
  gotcha: "Use Mock(spec=redis.Redis) for proper mocking"
  line: 318-390
```

### Current Codebase tree

```bash
src/
├── app.py                           # Main Flask app with /health endpoint (line 526)
├── config/
│   └── redis_config.py             # Redis client getter
└── core/
    └── services/
        └── health_monitor.py       # HealthMonitor service with Redis check

tests/
└── core/
    └── services/
        └── test_health_monitor_refactor.py  # Health check test patterns
```

### Desired Codebase tree with files to be added

```bash
# No new files - only modifying existing src/app.py
# Adding integration test:

tests/
└── integration/
    └── test_health_endpoint.py     # NEW: Integration test for /health endpoint
```

### Known Gotchas of our codebase & Library Quirks

```python
# CRITICAL: Flask health endpoints should NOT require authentication
# Current implementation at src/app.py:526 has @login_required
# Health checks must be accessible to monitoring systems without auth

# CRITICAL: HealthMonitor service already exists and works
# Located at src/core/services/health_monitor.py
# Has _check_redis_health() method that:
#   - Pings Redis
#   - Tests set/get/delete operations
#   - Measures response time
#   - Returns HealthStatus(status='healthy'|'degraded'|'error', response_time_ms=X, message=Y)

# CRITICAL: Health check caching for performance
# Best practice: Cache results to avoid hammering Redis on every health check
# Recommended: 27s cache for success, 9s cache for failures
# TickStock target: <50ms health check response time

# CRITICAL: HTTP status codes matter
# 200 = Healthy (all components ok)
# 503 = Service Unavailable (Redis or other critical component down)
# Load balancers use these codes for routing decisions

# CRITICAL: Redis client initialization
# Use src/config/redis_config.get_redis_client()
# Handle case where Redis URL not configured (returns None from app.py:115)

# CRITICAL: HealthStatus dataclass from health_monitor.py
# Fields: status, response_time_ms, last_check, message, details
# Use asdict() to convert to JSON-serializable dict

# TickStock-Specific Gotchas (inherited from template)
# CRITICAL: TickStockAppV2 is CONSUMER ONLY
# - This feature only checks connectivity, doesn't publish/subscribe
# - Read-only access pattern

# CRITICAL: Performance monitoring
# - Health check must be <50ms total
# - Redis ping target: <10ms
# - If Redis slow (>50ms), mark as 'degraded' not 'error'
```

## Implementation Blueprint

### Data models and structure

No new data models needed - using existing `HealthStatus` dataclass from `health_monitor.py`:

```python
@dataclass
class HealthStatus:
    status: str  # 'healthy', 'degraded', 'error', 'unknown'
    response_time_ms: float | None = None
    last_check: float | None = None
    message: str | None = None
    details: dict[str, Any] | None = None
```

### Implementation Tasks (ordered by dependencies)

```yaml
Task 1: MODIFY src/app.py - Update /health endpoint
  - LOCATION: Line 526-530 (current health_check function)
  - REMOVE: @login_required decorator (health checks must be unauthenticated)
  - IMPLEMENT:
      1. Import HealthMonitor from src.core.services.health_monitor
      2. Initialize HealthMonitor with config and redis_client
      3. Call health_monitor._check_redis_health()
      4. Convert HealthStatus to dict using dataclasses.asdict()
      5. Return comprehensive health response
  - FOLLOW pattern: Existing /api/health/redis at line 532 (but simpler)
  - NAMING: Keep function name health_check(), route '/health'
  - ERROR HANDLING: If Redis unavailable, return 503 status code
  - PERFORMANCE: Add timing measurement, log if >50ms

Task 2: CREATE tests/integration/test_health_endpoint.py
  - IMPLEMENT: Integration test for /health endpoint
  - FOLLOW pattern: tests/core/services/test_health_monitor_refactor.py (Redis mocking)
  - TEST COVERAGE:
      - GET /health returns 200 when Redis healthy
      - Response includes status, version, components, timestamp
      - GET /health returns 503 when Redis unavailable
      - Response time < 50ms (performance test)
  - MOCK: Redis client using unittest.mock.Mock(spec=redis.Redis)
  - ASSERTIONS:
      - assert response.status_code == 200
      - assert 'components' in response.json
      - assert response.json['components']['redis']['status'] == 'healthy'
  - PLACEMENT: tests/integration/ directory

Task 3: RUN validation gates
  - LEVEL 1: ruff check src/app.py --fix && ruff format src/app.py
  - LEVEL 2: python -m pytest tests/integration/test_health_endpoint.py -v
  - LEVEL 3: python run_tests.py
  - LEVEL 4: Manual curl test: curl http://localhost:5000/health
```

### Implementation Patterns & Key Details

```python
# Pattern 1: Enhanced Health Check Endpoint
# File: src/app.py (modify existing function at line 526)

from dataclasses import asdict
import time
from src.core.services.health_monitor import HealthMonitor

# REMOVE @login_required decorator - health checks must be unauthenticated
@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring systems.

    Returns comprehensive health status including Redis connectivity.
    Target response time: <50ms
    """
    start_time = time.time()

    # Initialize health data
    health_data = {
        "status": "healthy",
        "version": APP_VERSION,
        "components": {},
        "timestamp": time.time()
    }

    # Check Redis health using existing HealthMonitor
    try:
        # PATTERN: Reuse existing HealthMonitor service
        config = get_config()  # From src.core.services.config_manager
        health_monitor = HealthMonitor(config, redis_client=redis_client)

        # Get Redis health status
        redis_health = health_monitor._check_redis_health()

        # PATTERN: Convert HealthStatus dataclass to dict
        health_data['components']['redis'] = {
            'status': redis_health.status,
            'response_time_ms': redis_health.response_time_ms,
            'message': redis_health.message
        }

        # CRITICAL: Set overall status based on component health
        if redis_health.status == 'error':
            health_data['status'] = 'unhealthy'
            response_code = 503  # Service Unavailable
        elif redis_health.status == 'degraded':
            health_data['status'] = 'degraded'
            response_code = 200  # Still operational
        else:
            response_code = 200

    except Exception as e:
        # GOTCHA: If HealthMonitor fails, return error status
        logger.error(f"HEALTH-CHECK: Failed to check Redis: {e}")
        health_data['components']['redis'] = {
            'status': 'error',
            'response_time_ms': None,
            'message': f"Health check failed: {str(e)}"
        }
        health_data['status'] = 'unhealthy'
        response_code = 503

    # PERFORMANCE: Log slow health checks
    response_time = (time.time() - start_time) * 1000
    if response_time > 50:
        logger.warning(f"HEALTH-CHECK: Slow response: {response_time:.2f}ms (target: <50ms)")

    return jsonify(health_data), response_code


# Pattern 2: Integration Test for Health Endpoint
# File: tests/integration/test_health_endpoint.py (NEW FILE)

import pytest
from unittest.mock import Mock, patch
import redis
from src.core.services.health_monitor import HealthStatus

class TestHealthEndpoint:
    """Integration tests for /health endpoint."""

    @pytest.fixture
    def mock_redis_healthy(self):
        """Mock Redis client in healthy state."""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.ping.return_value = True
        mock_redis.set.return_value = True
        mock_redis.get.return_value = 'test_value'
        mock_redis.delete.return_value = 1
        mock_redis.info.return_value = {'redis_version': '6.2.0'}
        return mock_redis

    def test_health_endpoint_redis_healthy(self, client, mock_redis_healthy):
        """Test /health endpoint when Redis is healthy."""
        with patch('src.app.redis_client', mock_redis_healthy):
            response = client.get('/health')

            assert response.status_code == 200
            data = response.json

            # Validate response structure
            assert 'status' in data
            assert 'version' in data
            assert 'components' in data
            assert 'timestamp' in data

            # Validate Redis component
            assert 'redis' in data['components']
            assert data['components']['redis']['status'] == 'healthy'
            assert data['components']['redis']['response_time_ms'] is not None
            assert data['status'] == 'healthy'

    def test_health_endpoint_redis_unavailable(self, client):
        """Test /health endpoint when Redis is unavailable."""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.ping.side_effect = redis.ConnectionError("Connection refused")

        with patch('src.app.redis_client', mock_redis):
            response = client.get('/health')

            assert response.status_code == 503
            data = response.json

            assert data['status'] == 'unhealthy'
            assert data['components']['redis']['status'] == 'error'
            assert 'Connection refused' in str(data['components']['redis']['message'])

    def test_health_endpoint_no_authentication_required(self, client):
        """Test /health endpoint is accessible without authentication."""
        # Should work without login
        response = client.get('/health')
        assert response.status_code in [200, 503]  # Either healthy or unhealthy, but not 401

    def test_health_endpoint_performance(self, client, mock_redis_healthy):
        """Test /health endpoint meets <50ms performance target."""
        import time

        with patch('src.app.redis_client', mock_redis_healthy):
            start_time = time.time()
            response = client.get('/health')
            response_time = (time.time() - start_time) * 1000

            assert response.status_code == 200
            assert response_time < 50, f"Health check took {response_time:.2f}ms, should be <50ms"
```

### Integration Points

```yaml
# No new integrations - modifying existing endpoint

FLASK_ROUTE:
  - endpoint: "/health"
  - method: "GET"
  - file: "src/app.py"
  - line: 526
  - authentication: "REMOVE @login_required decorator"

HEALTH_MONITOR_SERVICE:
  - service: "src/core/services/health_monitor.py"
  - method: "HealthMonitor._check_redis_health()"
  - returns: "HealthStatus dataclass"
  - usage: "Reuse existing service, no duplication"

REDIS_CLIENT:
  - initialization: "src/config/redis_config.get_redis_client()"
  - usage: "Pass to HealthMonitor constructor"
  - error_handling: "Handle case where redis_client is None"

HTTP_STATUS_CODES:
  - 200: "Healthy or degraded (still operational)"
  - 503: "Unhealthy (critical component unavailable)"
```

## Validation Loop

### Level 1: Syntax & Style (Immediate Feedback)

```bash
# TickStock Standard: Ruff for linting and formatting

# Validate modified file
ruff check src/app.py --fix
ruff format src/app.py

# Validate new test file
ruff check tests/integration/test_health_endpoint.py --fix
ruff format tests/integration/test_health_endpoint.py

# Expected: Zero errors
```

### Level 2: Unit Tests (Component Validation)

```bash
# Run new integration test
python -m pytest tests/integration/test_health_endpoint.py -v

# Expected output:
# test_health_endpoint_redis_healthy PASSED
# test_health_endpoint_redis_unavailable PASSED
# test_health_endpoint_no_authentication_required PASSED
# test_health_endpoint_performance PASSED

# Run existing health monitor tests (ensure not broken)
python -m pytest tests/core/services/test_health_monitor_refactor.py -v

# Expected: All existing tests still pass
```

### Level 3: Integration Testing (System Validation - MANDATORY)

```bash
# TickStock MANDATORY Integration Tests
python run_tests.py

# Expected: 2+ tests passing, ~30 second runtime

# Manual curl tests (with services running)
# Test 1: Health check when Redis available
curl http://localhost:5000/health | jq .
# Expected:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "components": {
#     "redis": {
#       "status": "healthy",
#       "response_time_ms": 8.5,
#       "message": null
#     }
#   },
#   "timestamp": 1642234567.89
# }

# Test 2: Response time check
time curl -o /dev/null -s -w '%{time_total}\n' http://localhost:5000/health
# Expected: < 0.050 (50ms)

# Test 3: HTTP status code when healthy
curl -I http://localhost:5000/health
# Expected: HTTP/1.1 200 OK

# Test 4: No authentication required
curl -I http://localhost:5000/health
# Expected: 200 or 503, NOT 401 Unauthorized
```

### Level 4: TickStock-Specific Validation

```bash
# Performance measurement
# Verify health check meets <50ms target

# Add timing logs in implementation and check output:
grep "HEALTH-CHECK" logs/tickstock.log | tail -5
# Expected: All checks < 50ms

# No slow queries (health check shouldn't query database)
# Health check only pings Redis, no DB access

# No authentication required (critical for monitoring systems)
# Already validated in Level 3 manual tests

# Redis connectivity properly detected
# Test by stopping Redis: redis-cli shutdown
# Then: curl http://localhost:5000/health
# Expected: 503 status code, redis.status == 'error'
```

## Final Validation Checklist

### Technical Validation

- [ ] All 4 validation levels completed successfully
- [ ] Integration tests pass: `python run_tests.py` (MANDATORY)
- [ ] No linting errors: `ruff check src/`
- [ ] No formatting issues: `ruff format src/ --check`
- [ ] New test file passes: `python -m pytest tests/integration/test_health_endpoint.py -v`

### Feature Validation

- [ ] `/health` endpoint returns JSON with components.redis status
- [ ] HTTP status code 200 when healthy, 503 when Redis down
- [ ] Response time < 50ms (verified with curl timing)
- [ ] No authentication required (monitoring systems can access)
- [ ] Existing HealthMonitor service reused (no code duplication)

### TickStock Architecture Validation

- [ ] Component role respected (Consumer - read-only)
- [ ] No Redis pub-sub subscriptions (health check only)
- [ ] No database queries (health check is Redis-only)
- [ ] Performance target met (<50ms response time)
- [ ] No architectural violations

### Code Quality Validation

- [ ] Follows existing Flask route patterns in app.py
- [ ] Reuses HealthMonitor service (DRY principle)
- [ ] Proper error handling (try-except with logging)
- [ ] HTTP status codes follow standards (200/503)
- [ ] Test coverage includes happy path + error cases + performance
- [ ] Code structure limits followed (<50 lines for health_check function)
- [ ] Naming conventions: snake_case for function

### Documentation & Deployment

- [ ] Code is self-documenting with clear docstring
- [ ] Logs include performance warnings if slow
- [ ] No "Generated by Claude" comments

---

## Anti-Patterns to Avoid

### Generic Anti-Patterns
- ❌ Don't create new patterns when HealthMonitor service exists
- ❌ Don't skip integration tests (python run_tests.py is MANDATORY)
- ❌ Don't ignore response time performance (<50ms target)
- ❌ Don't add authentication to health endpoints (breaks monitoring)
- ❌ Don't hardcode Redis connection details

### TickStock-Specific Anti-Patterns

#### Feature-Specific Anti-Patterns
- ❌ **Don't keep @login_required decorator on /health**
  - Health checks must be unauthenticated for monitoring systems
  - Load balancers, Kubernetes probes need direct access
  - Violation: Keeping @login_required decorator

- ❌ **Don't duplicate Redis health check logic**
  - HealthMonitor service already checks Redis connectivity
  - Reuse existing _check_redis_health() method
  - Violation: Writing new redis.ping() code instead of using service

- ❌ **Don't return 200 when Redis is completely down**
  - 503 Service Unavailable is correct for critical component failure
  - Load balancers use status codes for routing
  - Violation: Returning 200 with {"redis": "error"} in body

- ❌ **Don't make health check slow**
  - Target: <50ms total response time
  - Redis ping should be <10ms
  - Violation: Adding database queries or complex logic to health check

- ❌ **Don't cache health check results**
  - Best practice for high-traffic production, but TickStock health checks are not high-traffic
  - Simple implementation first, optimize if needed
  - Note: External best practices recommend 27s/9s caching - consider for future if needed

---

## Success Metrics

**Confidence Score**: 9/10 for one-pass implementation success

**Reasoning**:
- ✅ Existing HealthMonitor service makes this straightforward
- ✅ Clear file locations and patterns identified (src/app.py:526)
- ✅ Test patterns well-documented in existing tests
- ✅ Simple enhancement, low complexity
- ⚠️ Minor: Need to handle case where redis_client is None (app startup edge case)

**Validation**: An AI agent with no prior TickStock knowledge should be able to:
1. Locate the /health endpoint at src/app.py:526
2. Import and use HealthMonitor service
3. Structure response with components.redis status
4. Write integration tests following existing patterns
5. Validate with curl and run_tests.py
